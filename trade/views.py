from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from .models import Order, News, Transport, CustomUser
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.conf import settings
from .models import Notification, Industry, Collect
from django.db.models import Q
from django.http import JsonResponse
import os
# Import translation function for internationalization
from django.utils.translation import gettext as _

# Get the current project's user model (automatically adapt to CustomUser)
User = get_user_model()

# Home page: No login required
def index(request):
    # Latest 3 supply orders (flag="1" stands for supply)
    supply_orders = Order.objects.filter(flag="1").order_by("-create_time")[:3]
    # Latest 3 purchase orders (flag="2" stands for purchase)
    purchase_orders = Order.objects.filter(flag="2").order_by("-create_time")[:3]
    # Latest 3 industry news
    latest_news = News.objects.all().order_by("-create_time")[:3]
    context = {
        "supply_orders": supply_orders,
        "purchase_orders": purchase_orders,
        "latest_news": latest_news,
    }
    return render(request, "index.html", context)

# Login view
def login(request):
    # Get the jump source (e.g., jump to login from the publish page)
    next_url = request.GET.get('next', '/')
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        next_url = request.POST.get('next', '/')
        # Verify username and password
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Login the user
            auth_login(request, user)
            # Remember me: Set session expiration time (2 weeks by default, 30 days if checked)
            if remember:
                request.session.set_expiry(30 * 24 * 60 * 60)  # 30 days
            else:
                request.session.set_expiry(0)  # Expire when browser is closed
            # Redirect back to the original page
            return redirect(next_url)
        else:
            # Login failed: Return error message
            return render(request, 'accounts/login.html', {
                'error_msg': _('Username or password is incorrect, please try again'),
                'next': next_url
            })
    # GET request: Display login page
    return render(request, 'accounts/login.html', {'next': next_url})

# Logout view
def logout(request):
    auth_logout(request)
    return redirect('trade:index')

# Register view (basic version, can be extended later)
def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        if password != password2:
            return render(request, 'accounts/register.html', {'error_msg': _('Two passwords do not match')})
        if User.objects.filter(username=username).exists():
            return render(request, 'accounts/register.html', {'error_msg': _('Username already exists')})
        User.objects.create_user(username=username, password=password)
        return redirect('trade:login')
    return render(request, 'accounts/register.html')

@login_required
def profile(request):
    # Count unread notifications (retain original)
    unread_notification_count = request.user.notifications.filter(is_read=False).count()
    media_url = '/media/'  # Modify according to your media configuration, or import from settings
    if request.method == "POST":
        # Get form data
        role = request.POST.get('role', 'visitor')
        phone = request.POST.get('phone', '')
        company = request.POST.get('company', '').strip()
        position = request.POST.get('position', '').strip()
        avatar = request.FILES.get('avatar')
        # Core validation: Company and position cannot be empty when selecting enterprise/admin
        if role in ['enterprise', 'admin'] and (not company or not position):
            messages.error(request, _("Company and position are required when selecting Enterprise User/Administrator!"))
            return redirect(reverse('trade:profile'))
        # Start updating user information
        user = request.user
        # 1. Automatically set audit status to pending (False) when role is changed
        if user.role != role:
            user.is_audited = False
        user.role = role
        # 2. Update basic information
        user.phone = phone
        user.company = company
        user.position = position
        # 3. Update avatar (if uploaded)
        if avatar:
            user.avatar = avatar
        # 4. Save to database
        user.save()
        # Prompt message: Distinguish whether audit is required
        if role in ['enterprise', 'admin'] and not user.is_audited:
            messages.success(request, _("Personal information modified successfully! Role change has been submitted and will take effect after administrator approval!"))
        else:
            messages.success(request, _("Personal information modified successfully!"))
        return redirect(reverse('trade:profile'))
    # GET request: Render personal center page
    context = {
        'user': request.user,
        'unread_notification_count': unread_notification_count,
        'media_url': media_url
    }
    return render(request, 'profile.html', context)

# User-side notification center (pagination + delete function)
@login_required
def notification_center(request):
    """Notification center view: Automatically mark all notifications on the current page as read when entering the page"""
    # 1. Get all notifications of the current user (sorted in reverse order of creation time)
    notifications_all = Notification.objects.filter(user=request.user).order_by('-created_at')
    # 2. Pagination configuration (10 items per page)
    paginator = Paginator(notifications_all, 10)
    page = request.GET.get('page', 1)
    try:
        notifications = paginator.page(page)
    except PageNotAnInteger:
        notifications = paginator.page(1)
    except EmptyPage:
        notifications = paginator.page(paginator.num_pages)
    # 3. Core: Traverse notifications on the current page and automatically mark unread as read (key fix)
    # Note: Must traverse the current page data with notifications.object_list and save()
    for notice in notifications.object_list:
        if not notice.is_read:
            notice.is_read = True
            notice.save()  # Must call save() to write modifications to the database
    # 4. Recalculate unread count (update after marking)
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    # 5. Retain the original logic for deleting notifications
    if request.method == 'POST' and 'delete_notices' in request.POST:
        notice_ids = request.POST.getlist('notice_ids')
        if notice_ids:
            Notification.objects.filter(id__in=notice_ids, user=request.user).delete()
            messages.success(request, _("Successfully deleted %(count)d notifications!") % {'count': len(notice_ids)})
            return redirect(f"{reverse('trade:notification_center')}?page={page}")
    # 6. Template context
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
        'paginator': paginator,
        'current_page': page
    }
    return render(request, 'notification_center.html', context)

# ---------------------- Order related (login required) ----------------------
# My orders
@login_required
def my_orders(request):
    """My orders page view"""
    # Query orders of the current user
    supply_orders = Order.objects.filter(user=request.user, flag='1').order_by('-create_time')
    purchase_orders = Order.objects.filter(user=request.user, flag='2').order_by('-create_time')
    context = {
        'user': request.user,
        'supply_orders': supply_orders,
        'purchase_orders': purchase_orders,
    }
    return render(request, 'my_orders.html', context)

@login_required
def order_delete(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if not (request.user.is_audited and (request.user.role == 'enterprise' or request.user.role == 'admin')):
        messages.error(request, _("Only audited enterprise users/administrators can delete orders!"))
        return redirect(reverse('trade:my_orders'))
    order_title = order.title
    # Delete order image (if any)
    if order.image:
        image_path = os.path.join(settings.MEDIA_ROOT, str(order.image))
        if os.path.exists(image_path):
            os.remove(image_path)
    # Safely pass order=None now
    Notification.objects.create(
        user=request.user,
        message=_("Your order %(title)s has been deleted successfully!") % {'title': order_title},
        order=None,
        is_read=False
    )
    order.delete()
    messages.success(request, _("Order %(title)s has been deleted successfully!") % {'title': order_title})
    return redirect(reverse('trade:my_orders'))

# Order list (isolate purchase/supply by passing fixed flag via URL)
@login_required
def order_list(request, flag="1"):
    # 1. Basic query: Filter by flag
    order_queryset = Order.objects.filter(flag=flag).order_by("-create_time")
    # 2. Get filter parameters
    keyword = request.GET.get('keyword', '').strip()
    industry_id = request.GET.get('industry_id', '').strip()
    # 3. Industry filter logic
    selected_industry = None
    if industry_id and industry_id.isdigit():
        try:
            selected_industry = Industry.objects.get(id=industry_id)
            order_queryset = order_queryset.filter(industry_id=industry_id)
        except Industry.DoesNotExist:
            pass  # Do not filter if industry ID does not exist
    # 4. Keyword search logic
    if keyword:
        order_queryset = order_queryset.filter(
            Q(title__icontains=keyword) | Q(user__username__icontains=keyword)
        )
    # 5. Pagination logic
    paginator = Paginator(order_queryset, 3)
    page = request.GET.get("page", 1)
    try:
        page_num = int(page)
        page_num = max(1, min(page_num, paginator.num_pages))
        orders = paginator.page(page_num)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)
    # 6. Get all industries (for drop-down box rendering)
    industries = Industry.objects.all()
    return render(request, "order/list.html", {
        "orders": orders,
        "flag": flag,
        "keyword": keyword,
        "industries": industries,
        "selected_industry": selected_industry,
    })

@login_required
def order_create(request, flag="1"):
    # Add: Audit + role permission verification
    # Only audited enterprise users/administrators can publish orders
    if not (request.user.is_audited and (request.user.role == 'enterprise' or request.user.role == 'admin')):
        messages.error(request, _("Only audited enterprise users/administrators can publish orders, please complete role audit first!"))
        # Redirect to the corresponding order list page according to flag
        if flag == "1":
            return redirect(reverse('trade:supply_list'))
        else:
            return redirect(reverse('trade:purchase_list'))
    if request.method == "POST":
        # 1. Get form data (add contact_phone and nationality)
        title = request.POST.get('title')
        content = request.POST.get('content')
        industry_id = request.POST.get('industry')
        end_time = request.POST.get('end_time')
        transport_id = request.POST.get('transport')
        image = request.FILES.get('image')
        image_url = request.POST.get('image_url')
        contact_phone = request.POST.get('contact_phone', '').strip()
        nationality = request.POST.get('nationality', '').strip()
        # 2. Create order (save contact_phone and nationality fields)
        order = Order.objects.create(
            title=title,
            content=content,
            flag=flag,
            user=request.user,
            industry_id=industry_id if industry_id else None,
            transport_id=transport_id if transport_id else None,
            end_time=end_time if end_time else None,
            image=image,
            image_url=image_url,
            contact_phone=contact_phone,
            nationality=nationality
        )
        # 3. Send notification to the publisher
        order_type = _("Supply") if flag == "1" else _("Purchase")
        Notification.objects.create(
            user=request.user,
            order=order,
            message=_("Your %(type)s order %(title)s has been published successfully!") % {'type': order_type, 'title': order.title}
        )
        # 4. Send notification to all administrators
        admin_users = CustomUser.objects.filter(role="admin")
        for admin_user in admin_users:
            Notification.objects.create(
                user=admin_user,
                order=order,
                message=_("User %(username)s has added a new %(type)s order: %(title)s, please review it in a timely manner!") % {'username': request.user.username, 'type': order_type, 'title': order.title}
            )
        messages.success(request, _("Order published successfully!"))
        return redirect(reverse('trade:order_detail', kwargs={'order_id': order.id}))
    # GET request: Render create page
    industries = Industry.objects.all()
    transports = Transport.objects.all()
    context = {
        'flag': flag,
        'industries': industries,
        'transports': transports
    }
    return render(request, 'order/create.html', context)

# Order detail (viewable by all, keep @login_required if needed, no modification)
@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    # Pre-calculate whether the current user has collected this order
    is_collected = False
    if request.user.is_authenticated:
        is_collected = Collect.objects.filter(user=request.user, order=order).exists()
    context = {
        'order': order,
        'is_collected': is_collected,
    }
    return render(request, 'order/detail.html', context)

# Order edit (only publishers + audited enterprise/administrators can edit)
@login_required
def order_edit(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    # Add: Audit + role permission verification
    # Only audited enterprise users/administrators can edit orders
    if not (request.user.is_audited and (request.user.role == 'enterprise' or request.user.role == 'admin')):
        messages.error(request, _("Only audited enterprise users/administrators can edit orders, please complete role audit first!"))
        return redirect(reverse('trade:order_detail', kwargs={'order_id': order_id}))
    if request.method == "POST":
        # 1. Update order data (add contact_phone and nationality fields)
        order.title = request.POST.get('title')
        order.content = request.POST.get('content')
        order.status = request.POST.get('status')
        order.industry_id = request.POST.get('industry') if request.POST.get('industry') else None
        order.transport_id = request.POST.get('transport') if request.POST.get('transport') else None
        order.end_time = request.POST.get('end_time') if request.POST.get('end_time') else None
        order.image_url = request.POST.get('image_url')
        # Add: Receive and save contact phone and nationality
        order.contact_phone = request.POST.get('contact_phone', '').strip()
        order.nationality = request.POST.get('nationality', '').strip()
        # Image update (original logic)
        if request.FILES.get('image'):
            # Delete old image
            if order.image:
                old_image_path = os.path.join(settings.MEDIA_ROOT, str(order.image))
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            order.image = request.FILES.get('image')
        # Save order (including new fields)
        order.save()
        # 2. Send notification to the publisher
        order_type = _("Supply") if order.flag == "1" else _("Purchase")
        Notification.objects.create(
            user=request.user,
            order=order,
            message=_("Your %(type)s order %(title)s has been modified successfully!") % {'type': order_type, 'title': order.title}
        )
        # 3. Send notification to all administrators
        admin_users = CustomUser.objects.filter(role="admin")
        for admin_user in admin_users:
            Notification.objects.create(
                user=admin_user,
                order=order,
                message=_("User %(username)s has modified a %(type)s order: %(title)s, please check it!") % {'username': request.user.username, 'type': order_type, 'title': order.title}
            )
        messages.success(request, _("Order modified successfully!"))
        return redirect(reverse('trade:order_detail', kwargs={'order_id': order.id}))
    # GET request: Render edit page
    industries = Industry.objects.all()
    transports = Transport.objects.all()
    context = {
        'order': order,
        'industries': industries,
        'transports': transports
    }
    return render(request, 'order/edit.html', context)

# ---------------------- Logistics related ----------------------
# Logistics list page (with search + classification + pagination)
@login_required
def transport_list(request):
    # 1. Basic query: Sorted in reverse order of creation time
    transport_queryset = Transport.objects.all().order_by('-create_time')
    # 2. Get front-end parameters
    keyword = request.GET.get('keyword', '').strip()  # Name keyword
    type = request.GET.get('type', '').strip()  # Logistics type (air/sea/land)
    page = request.GET.get('page', 1)  # Page number, default page 1
    # 3. Keyword filter (fuzzy match by name)
    if keyword:
        transport_queryset = transport_queryset.filter(Q(name__icontains=keyword))
    # 4. Type filter
    if type:
        transport_queryset = transport_queryset.filter(type=type)
    # 5. Pagination processing: 6 items per page
    paginator = Paginator(transport_queryset, 6)
    transport_list = paginator.get_page(page)
    # 6. Assemble context
    context = {
        'transport_list': transport_list,
        'keyword': keyword,
        'type': type,
    }
    return render(request, 'transport/list.html', context)

# Logistics detail page (unchanged)
@login_required
def transport_detail(request, transport_id):
    transport = get_object_or_404(Transport, id=transport_id)
    return render(request, 'transport/detail.html', {'transport': transport})

# ---------------------- News related (login required) ----------------------
# News list page (with search + classification + pagination)
@login_required
def news_list(request):
    # 1. Basic query: Sorted in reverse order of publish time
    news_queryset = News.objects.all().order_by('-create_time')
    # 2. Get front-end parameters
    keyword = request.GET.get('keyword', '').strip()  # Search keyword
    category = request.GET.get('category', '').strip()  # Classification filter
    page = request.GET.get('page', 1)  # Page number, default page 1
    # 3. Keyword filter (fuzzy match by title)
    if keyword:
        news_queryset = news_queryset.filter(Q(title__icontains=keyword))
    # 4. Classification filter
    if category:
        news_queryset = news_queryset.filter(category=category)
    # 5. Pagination processing: 3 items per page
    paginator = Paginator(news_queryset, 3)
    news_list = paginator.get_page(page)
    # 6. Assemble context
    context = {
        'news_list': news_list,
        'keyword': keyword,
        'category': category,
    }
    return render(request, 'news/list.html', context)

# News detail view (fix collection status judgment)
@login_required
def news_detail(request, news_id):
    news = get_object_or_404(News, id=news_id)
    # Core fix: Pre-calculate whether the current user has collected this news
    is_collected = False
    if request.user.is_authenticated:
        is_collected = Collect.objects.filter(user=request.user, news=news).exists()
    context = {
        'news': news,
        'is_collected': is_collected,
    }
    return render(request, 'news/detail.html', context)

# ---------------------- About us (no login required) ----------------------
# About us page (remove @login_required decorator if no login is required)
# @login_required  # Delete this line if visitors are allowed to access
def about_us(request):
    # System core information (can be moved to configuration file/database later)
    system_info = {
        'name': _('Cross_border Trade Supply and Demand Matching Platform'),
        'address': _('15th Floor, UK-China Economic and Trade Building, Nangang District, Harbin City, Heilongjiang Province, China'),
        'phone': '400-888-9999',
        'email': 'service@cn-rus-trade.com',
        'description': _('This platform focuses on the matching of Cross_border trade supply and demand information, provides integrated procurement, supply and logistics solutions for enterprises, and helps the efficient development of different country cross-border trade.')
    }
    return render(request, 'about.html', {
        'system_info': system_info
    })

# ---------------------- Collection ----------------------
@login_required
def my_collections(request):
    # 1. Query all collections of the current user (key: must filter user=request.user)
    collects = Collect.objects.filter(user=request.user).order_by('-create_time')
    print("Current user's collection count: ", collects.count())  # Print in terminal to verify data existence
    # 2. Split supply orders/purchase orders/news collections
    supply_collects_all = []
    purchase_collects_all = []
    news_collects_all = []
    for coll in collects:
        if coll.order:  # Collected an order
            if coll.order.flag == "1":  # Supply order (1=supply/2=purchase according to your flag value)
                supply_collects_all.append(coll)
            elif coll.order.flag == "2":  # Purchase order
                purchase_collects_all.append(coll)
        elif coll.news:  # Collected news
            news_collects_all.append(coll)
    # 3. Pagination configuration (3 items per page)
    supply_page = request.GET.get('supply_page', 1)
    supply_paginator = Paginator(supply_collects_all, 3)
    supply_collects = supply_paginator.get_page(supply_page)

    purchase_page = request.GET.get('purchase_page', 1)
    purchase_paginator = Paginator(purchase_collects_all, 3)
    purchase_collects = purchase_paginator.get_page(purchase_page)

    news_page = request.GET.get('news_page', 1)
    news_paginator = Paginator(news_collects_all, 3)
    news_collects = news_paginator.get_page(news_page)

    context = {
        'supply_collects': supply_collects,
        'purchase_collects': purchase_collects,
        'news_collects': news_collects,
        'supply_paginator': supply_paginator,
        'purchase_paginator': purchase_paginator,
        'news_paginator': news_paginator,
        'supply_page': supply_page,
        'purchase_page': purchase_page,
        'news_page': news_page,
    }
    return render(request, 'my_collections.html', context)

# Collect/cancel collect order
@login_required
def collect_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == "POST":
        # Check if already collected
        collect, created = Collect.objects.get_or_create(
            user=request.user,
            order=order,
            defaults={'news': None}  # Ensure news field is empty
        )
        if not created:
            # Already collected → Delete
            collect.delete()
            action = "cancel"
        else:
            # Not collected → Create
            action = "collect"
        # AJAX response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'action': action})
    return redirect('trade:order_detail', order_id=order_id)

# Collect/cancel collect news
@login_required
def collect_news(request, news_id):
    news = get_object_or_404(News, id=news_id)
    if request.method == "POST":
        # Check if already collected
        collect, created = Collect.objects.get_or_create(
            user=request.user,
            news=news,
            defaults={'order': None}  # Ensure order field is empty
        )
        if not created:
            # Already collected → Delete
            collect.delete()
            action = "cancel"
        else:
            # Not collected → Create
            action = "collect"
        # AJAX response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'action': action})
    return redirect('trade:news_detail', news_id=news_id)


# Add at the end of views.py (keep other existing code)
def switch_language(request):
    """
    Switch website display language (English/Chinese) and redirect back to original page
    Store selected language in user session to persist across requests
    :param request: Django HttpRequest object
    :return: Redirect response to original page
    """
    # Get target language (default to English if not provided)
    lang = request.GET.get('lang', 'en')
    # Get return URL (default to homepage if not provided)
    next_url = request.GET.get('next', '/')

    # Only allow 'en' (English) or 'zh' (Chinese) to avoid invalid values
    if lang in ['en', 'zh']:
        request.session['site_language'] = lang  # Save language preference to session

    # Redirect back to the page where the language switch was triggered
    return redirect(next_url)