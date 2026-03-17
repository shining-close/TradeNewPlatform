from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.hashers import make_password
from django.http import QueryDict

from administrator.forms import TransportAddForm
from trade.models import CustomUser, Order, Company, Transport, News, Industry

# ---------------------- Core Permission Control (Compatible with existing CustomUser role=admin) ----------------------
def is_admin_user(user):
    """
    Double verification:
    1. User is authenticated
    2. Is Django superuser OR custom role is admin
    """
    return user.is_authenticated and (user.is_superuser or user.role == "admin")

def admin_auth_required(view_func):
    """Decorator for admin permission verification"""
    def wrapper(request, *args, **kwargs):
        if not is_admin_user(request.user):
            messages.error(request, "No administrator permission, access denied!")
            return redirect('trade:index')  # Redirect to user front page
        return view_func(request, *args, **kwargs)
    return wrapper


# ---------------------- Admin Dashboard (Data Visualization) ----------------------
@admin_auth_required
def dashboard(request):
    """Dashboard: Statistics of core platform data (based on existing trade models)"""
    data = {
        # User statistics
        'total_users': CustomUser.objects.count(),
        'enterprise_users': CustomUser.objects.filter(role="enterprise").count(),
        'audited_enterprise': CustomUser.objects.filter(role="enterprise", is_audited=True).count(),
        # Order statistics
        'total_orders': Order.objects.count(),
        'supply_orders': Order.objects.filter(flag="1").count(),
        'demand_orders': Order.objects.filter(flag="2").count(),
        'completed_orders': Order.objects.filter(status="completed").count(),
        # Other statistics
        'total_transport': Transport.objects.count(),
        'total_news': News.objects.count(),
    }
    return render(request, 'administrator/dashboard.html', data)

# ---------------------- User Management ----------------------
@admin_auth_required
def user_manage(request):
    """
    User management page:
    - Support batch delete + single delete
    - Nationality display
    - Unaudited filter
    """
    # 1. Get filter parameters
    role = request.GET.get('role')
    keyword = request.GET.get('keyword', '').strip()
    audit = request.GET.get('audit')

    # 2. Handle batch delete (POST request)
    if request.method == 'POST' and 'batch_delete' in request.POST:
        user_ids = request.POST.getlist('user_ids')
        # Verify if users are selected
        if not user_ids:
            messages.error(request, "Please select users to delete first!")
            # Reconstruct filter parameters for redirect
            query_params = QueryDict(mutable=True)
            if role: query_params['role'] = role
            if keyword: query_params['keyword'] = keyword
            if audit: query_params['audit'] = audit
            return redirect(f"{reverse('administrator:user_manage')}?{query_params.urlencode()}")

        # Batch delete logic with permission verification
        deleted_count = 0
        for user_id in user_ids:
            try:
                user = CustomUser.objects.get(id=user_id)
                # Forbid deleting superadmin
                if user.is_superuser:
                    messages.warning(request, f"User [{user.username}] is super administrator, deletion forbidden!")
                    continue
                # Forbid deleting current logged-in user
                if user.id == request.user.id:
                    messages.warning(request, f"Deletion of current logged-in account [{user.username}] forbidden!")
                    continue
                # Execute deletion
                username = user.username
                user.delete()
                deleted_count += 1
                messages.success(request, f"User [{username}] deleted successfully!")
            except CustomUser.DoesNotExist:
                messages.error(request, f"User with ID {user_id} does not exist, deletion failed!")
            except Exception as e:
                messages.error(request, f"Failed to delete user ID {user_id}: {str(e)}")

        # Return to filtered page after batch delete
        query_params = QueryDict(mutable=True)
        if role: query_params['role'] = role
        if keyword: query_params['keyword'] = keyword
        if audit: query_params['audit'] = audit
        return redirect(f"{reverse('administrator:user_manage')}?{query_params.urlencode()}")

    # 3. Original filter logic (role + keyword + unaudited)
    users = CustomUser.objects.all().order_by('-id')
    if keyword:
        users = users.filter(username__icontains=keyword)
    if role:
        users = users.filter(role=role)
    if audit == 'unreviewed':
        users = users.filter(role='enterprise', is_audited=False)

    # 4. Pagination logic (fixed page number exception)
    paginator = Paginator(users, 10)
    page_str = request.GET.get('page', '1')
    try:
        page = int(page_str)
        if page < 1:
            page = 1
        page_users = paginator.page(page)
    except PageNotAnInteger:
        page_users = paginator.page(1)
    except EmptyPage:
        page_users = paginator.page(paginator.num_pages)

    # 5. Context parameters
    context = {
        'users': page_users,
        'current_role': role,
        'current_keyword': keyword,
        'paginator': paginator,
        'current_audit': audit
    }
    return render(request, 'administrator/user_manage.html', context)


@admin_auth_required
def user_audit(request, user_id):
    """Enterprise user audit view (original logic, no modification)"""
    user = get_object_or_404(CustomUser, id=user_id)
    if user.role == "enterprise":
        user.is_audited = not user.is_audited
        user.save()
        msg = "approved" if user.is_audited else "rejected"
        messages.success(request, f"User {msg} successfully!")
    else:
        messages.error(request, "Only enterprise users can be audited!")
    return redirect('administrator:user_manage')


@admin_auth_required
def user_add(request):
    """Add new user view (include nationality field, no modification)"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        phone = request.POST.get('phone', '')
        company = request.POST.get('company', '')
        position = request.POST.get('position', '')
        role = request.POST.get('role')
        nationality = request.POST.get('nationality', '')
        is_audited = request.POST.get('is_audited') == 'on'

        # Required fields verification
        if not all([username, password, role]):
            messages.error(request, "Username, password and role are required fields!")
            return redirect('administrator:user_add')
        # Username uniqueness verification
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "This username already exists, please change it!")
            return redirect('administrator:user_add')

        try:
            # Create user (include nationality field)
            user = CustomUser(
                username=username,
                password=make_password(password),
                phone=phone,
                company=company,
                position=position,
                nationality=nationality,
                role=role,
                is_audited=is_audited if role == "enterprise" else False
            )
            # Handle avatar upload
            if request.FILES.get('avatar'):
                user.avatar = request.FILES.get('avatar')
            user.save()
            messages.success(request, f"User [{username}] added successfully!")
            return redirect('administrator:user_manage')
        except Exception as e:
            messages.error(request, f"Failed to add user: {str(e)}")
            return redirect('administrator:user_add')

    # Pass role choices to template
    context = {
        'role_choices': CustomUser.ROLE_CHOICES,
        'is_edit': False
    }
    return render(request, 'administrator/user_form.html', context)


@admin_auth_required
def user_edit(request, user_id):
    """Edit user view (include nationality field, no modification)"""
    user = get_object_or_404(CustomUser, id=user_id)
    # Permission verification: forbid editing superadmin/self
    if user.is_superuser or user.id == request.user.id:
        messages.error(request, "Forbidden to edit super administrator/own information!")
        return redirect('administrator:user_manage')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password', '')
        phone = request.POST.get('phone', '')
        company = request.POST.get('company', '')
        position = request.POST.get('position', '')
        role = request.POST.get('role')
        nationality = request.POST.get('nationality', '')
        is_audited = request.POST.get('is_audited') == 'on'

        # Required fields verification
        if not all([username, role]):
            messages.error(request, "Username and role are required fields!")
            return redirect('administrator:user_edit', user_id=user_id)
        # Username uniqueness verification (exclude self)
        if CustomUser.objects.filter(username=username).exclude(id=user_id).exists():
            messages.error(request, "This username already exists, please change it!")
            return redirect('administrator:user_edit', user_id=user_id)

        try:
            # Update user information (include nationality field)
            user.username = username
            if password:
                user.password = make_password(password)
            user.phone = phone
            user.company = company
            user.position = position
            user.nationality = nationality
            user.role = role
            user.is_audited = is_audited if role == "enterprise" else False
            # Handle avatar update
            if request.FILES.get('avatar'):
                user.avatar = request.FILES.get('avatar')
            user.save()
            messages.success(request, f"User [{username}] updated successfully!")
            return redirect('administrator:user_manage')
        except Exception as e:
            messages.error(request, f"Failed to update user: {str(e)}")
            return redirect('administrator:user_edit', user_id=user_id)

    # Context parameters
    context = {
        'user': user,
        'role_choices': CustomUser.ROLE_CHOICES,
        'is_edit': True
    }
    return render(request, 'administrator/user_form.html', context)


@admin_auth_required
def user_delete(request, user_id):
    """Single user delete view (original logic, no modification)"""
    user = get_object_or_404(CustomUser, id=user_id)
    # Permission verification: forbid deleting superadmin
    if user.is_superuser:
        messages.error(request, "Forbidden to delete super administrator!")
        return redirect('administrator:user_manage')
    # Permission verification: forbid deleting self
    if user.id == request.user.id:
        messages.error(request, "Forbidden to delete current logged-in account!")
        return redirect('administrator:user_manage')

    # Execute deletion
    username = user.username
    try:
        user.delete()
        messages.success(request, f"User [{username}] deleted successfully!")
    except Exception as e:
        messages.error(request, f"Failed to delete user: {str(e)}")

    # Return to filtered page
    query_params = request.GET.copy()
    if query_params:
        param_str = '&'.join([f"{k}={v}" for k, v in query_params.items() if k != 'page'])
        return redirect(f"{reverse('administrator:user_manage')}?{param_str}")
    return redirect('administrator:user_manage')


# ---------------------- Order Management ----------------------
@admin_auth_required
def order_manage(request):
    """Order management list"""
    flag = request.GET.get('flag')
    status = request.GET.get('status')
    title_keyword = request.GET.get('title_keyword', '').strip()
    user_keyword = request.GET.get('user_keyword', '').strip()

    # 基础查询集
    orders = Order.objects.all().order_by('-create_time')

    # 组合搜索逻辑
    if title_keyword or user_keyword:
        query = Q()
        if title_keyword:
            query |= Q(title__icontains=title_keyword)

        # 核心修复：去掉多余的括号，使用 key=value 格式
        if user_keyword:
            query |= Q(user__username__icontains=user_keyword)

        orders = orders.filter(query)

    # 筛选条件
    if flag:
        orders = orders.filter(flag=flag)
    if status:
        orders = orders.filter(status=status)

    # 分页逻辑
    paginator = Paginator(orders, 10)
    page = request.GET.get('page', '1')
    try:
        page = int(page)
        if page < 1: page = 1
        page_orders = paginator.page(page)
    except (PageNotAnInteger, ValueError):
        page_orders = paginator.page(1)
    except EmptyPage:
        page_orders = paginator.page(paginator.num_pages)

    context = {
        'orders': page_orders,
        'current_flag': flag,
        'current_status': status,
        'current_title_keyword': title_keyword,
        'current_user_keyword': user_keyword,
        'paginator': paginator
    }
    return render(request, 'administrator/order_manage.html', context)


@admin_auth_required
def order_status(request, order_id):
    """Toggle Order Status"""
    order = get_object_or_404(Order, id=order_id)
    order.status = "completed" if order.status == "uncompleted" else "uncompleted"
    order.save()

    if request.session.get('site_language') == 'zh':
        messages.success(request, f"订单 [{order.title}] 状态更新成功！")
    else:
        messages.success(request, f"Order [{order.title}] status updated!")
    return redirect('administrator:order_manage')  # 修复：跳转列表页


@admin_auth_required
def order_add(request):
    """Add New Order"""
    if request.method == 'POST':
        title = request.POST.get('title')
        flag = request.POST.get('flag')
        status = request.POST.get('status')
        content = request.POST.get('content')
        industry_id = request.POST.get('industry', '')
        end_time = request.POST.get('end_time')
        user_id = request.POST.get('user')
        transport_id = request.POST.get('transport')
        image_url = request.POST.get('image_url', '')

        if not all([title, flag, status, content, user_id]):
            if request.session.get('site_language') == 'zh':
                messages.error(request, "标题、类型、状态、内容、发布人为必填项！")
            else:
                messages.error(request, "Title, type, status, content and publisher are required!")
            return redirect('administrator:order_add')

        try:
            user = get_object_or_404(CustomUser, id=user_id)
            transport = get_object_or_404(Transport, id=transport_id) if transport_id else None
            industry = get_object_or_404(Industry, id=industry_id) if industry_id else None

            order = Order(
                title=title, flag=flag, status=status, content=content, industry=industry,
                end_time=timezone.datetime.strptime(end_time, '%Y-%m-%dT%H:%M') if end_time else None,
                user=user, transport=transport, image_url=image_url
            )
            if request.FILES.get('image'): order.image = request.FILES.get('image')
            order.save()

            if request.session.get('site_language') == 'zh':
                messages.success(request, f"订单 [{order.title}] 新增成功！")
            else:
                messages.success(request, f"Order [{order.title}] added successfully!")
            return redirect('administrator:order_manage')  # 修复：跳转列表页

        except Exception as e:
            if request.session.get('site_language') == 'zh':
                messages.error(request, f"订单新增失败：{str(e)}")
            else:
                messages.error(request, f"Failed to add order: {str(e)}")
            return redirect('administrator:order_add')

    context = {
        'users': CustomUser.objects.all(),
        'transports': Transport.objects.all(),
        'industries': Industry.objects.all(),
        'is_edit': False
    }
    return render(request, 'administrator/order_form.html', context)


@admin_auth_required
def order_edit(request, order_id):
    """Edit Order"""
    try:
        order = get_object_or_404(Order, id=order_id)
    except Exception as e:
        if request.session.get('site_language') == 'zh':
            messages.error(request, f"订单不存在：{str(e)}")
        else:
            messages.error(request, f"Order does not exist: {str(e)}")
        return redirect('administrator:order_manage')  # 修复：跳转列表页

    if request.method == 'POST':
        title = request.POST.get('title')
        flag = request.POST.get('flag')
        status = request.POST.get('status')
        content = request.POST.get('content')
        industry_id = request.POST.get('industry', '')
        end_time = request.POST.get('end_time')
        user_id = request.POST.get('user')
        transport_id = request.POST.get('transport')
        image_url = request.POST.get('image_url', '')

        if not all([title, flag, status, content, user_id]):
            if request.session.get('site_language') == 'zh':
                messages.error(request, "标题、类型、状态、内容、发布人为必填项！")
            else:
                messages.error(request, "Title, type, status, content and publisher are required!")
            return redirect('administrator:order_edit', order_id=order_id)

        try:
            user = get_object_or_404(CustomUser, id=user_id)
            transport = get_object_or_404(Transport, id=transport_id) if transport_id else None
            industry = get_object_or_404(Industry, id=industry_id) if industry_id else None

            order.title = title
            order.flag = flag
            order.status = status
            order.content = content
            order.industry = industry

            if end_time:
                try:
                    order.end_time = timezone.datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
                except ValueError:
                    if request.session.get('site_language') == 'zh':
                        messages.error(request, "截止时间格式错误！")
                    else:
                        messages.error(request, "End time format error!")
                    return redirect('administrator:order_edit', order_id=order_id)
            else:
                order.end_time = None

            order.user = user
            order.transport = transport
            order.image_url = image_url
            if request.FILES.get('image'): order.image = request.FILES.get('image')
            order.save()

            if request.session.get('site_language') == 'zh':
                messages.success(request, f"订单 [{order.title}] 修改成功！")
            else:
                messages.success(request, f"Order [{order.title}] updated successfully!")

            # 最关键修复：修改成功后跳转到订单列表，而不是编辑页
            return redirect('administrator:order_manage')

        except Exception as e:
            if request.session.get('site_language') == 'zh':
                messages.error(request, f"订单修改失败：{str(e)}")
            else:
                messages.error(request, f"Failed to update order: {str(e)}")
            return redirect('administrator:order_edit', order_id=order_id)

    context = {
        'order': order,
        'users': CustomUser.objects.all(),
        'transports': Transport.objects.all(),
        'industries': Industry.objects.all(),
        'is_edit': True
    }
    return render(request, 'administrator/order_form.html', context)


@admin_auth_required
def order_delete(request, order_id):
    """Delete Order"""
    order = get_object_or_404(Order, id=order_id)
    title = order.title
    order.delete()

    if request.session.get('site_language') == 'zh':
        messages.success(request, f"订单 [{title}] 删除成功！")
    else:
        messages.success(request, f"Order [{title}] deleted successfully!")

    # 修复：跳转列表页
    return redirect('administrator:order_manage')

# ---------------------- Transport/News Management (Simplified Version) ----------------------
# Logistics management list (session-based zh/en switch only)
@admin_auth_required
def transport_manage(request):
    transport_list = Transport.objects.all().order_by('-create_time')
    # Search logic (keep original)
    search_key = request.GET.get('search', '')
    if search_key:
        transport_list = transport_list.filter(name__icontains=search_key)
    # Pagination logic (keep original: 10 items per page)
    paginator = Paginator(transport_list, 10)
    page = request.GET.get('page', 1)
    try:
        transports = paginator.page(page)
    except PageNotAnInteger:
        transports = paginator.page(1)
    except EmptyPage:
        transports = paginator.page(paginator.num_pages)
    return render(request, 'administrator/transport_manage.html', {
        'transports': transports,
        'search_key': search_key
    })

# Add new logistics record (session-based zh/en switch only)
@admin_auth_required
def transport_add(request):
    if request.method == 'POST':
        form = TransportAddForm(request.POST, request.FILES)
        if form.is_valid():
            transport = form.save(commit=False)
            transport.save()
            # Session-based success message (zh/en only)
            if request.session.get('site_language') == 'zh':
                messages.success(request, f"物流 [{transport.name}] 添加成功！")
            else:
                messages.success(request, f"Transport [{transport.name}] added successfully!")
            return redirect('administrator:transport_manage')
        else:
            # Session-based error message assembly (zh/en only)
            if request.session.get('site_language') == 'zh':
                error_msg = "保存失败："
                field_map = {
                    'name': '物流名称', 'type': '物流类型', 'price': '参考价格',
                    'time': '时效', 'company': '物流公司', 'description': '物流描述', 'image': '物流图片'
                }
            else:
                error_msg = "Failed to add: "
                field_map = {
                    'name': 'Logistics Name', 'type': 'Logistics Type', 'price': 'Reference Price',
                    'time': 'Delivery Time', 'company': 'Logistics Company', 'description': 'Logistics Description', 'image': 'Logistics Image'
                }
            for field, errors in form.errors.items():
                field_name = field_map.get(field, field)
                error_msg += f"{field_name}：{''.join(errors)}；"
            messages.error(request, error_msg.rstrip('；'))
    else:
        form = TransportAddForm()
    return render(request, 'administrator/transport_add.html', {'form': form})

# Edit logistics record (session-based zh/en switch only)
@admin_auth_required
def transport_edit(request, transport_id):
    transport = get_object_or_404(Transport, id=transport_id)
    if request.method == 'POST':
        form = TransportAddForm(request.POST, request.FILES, instance=transport)
        if form.is_valid():
            form.save()
            # Session-based success message (zh/en only)
            if request.session.get('site_language') == 'zh':
                messages.success(request, f"物流 [{transport.name}] 修改成功！")
            else:
                messages.success(request, f"Transport [{transport.name}] updated successfully!")
            return redirect('administrator:transport_manage')
        else:
            # Session-based error message assembly (zh/en only)
            if request.session.get('site_language') == 'zh':
                error_msg = "修改失败："
                field_map = {
                    'name': '物流名称', 'type': '物流类型', 'price': '参考价格',
                    'time': '时效', 'company': '物流公司', 'description': '物流描述', 'image': '物流图片'
                }
            else:
                error_msg = "Failed to update: "
                field_map = {
                    'name': 'Logistics Name', 'type': 'Logistics Type', 'price': 'Reference Price',
                    'time': 'Delivery Time', 'company': 'Logistics Company', 'description': 'Logistics Description', 'image': 'Logistics Image'
                }
            for field, errors in form.errors.items():
                field_name = field_map.get(field, field)
                error_msg += f"{field_name}：{''.join(errors)}；"
            messages.error(request, error_msg.rstrip('；'))
    else:
        form = TransportAddForm(instance=transport)
    return render(request, 'administrator/transport_edit.html', {'form': form, 'transport': transport})

# Delete logistics record (session-based zh/en switch only)
@admin_auth_required
def transport_delete(request, transport_id):
    transport = get_object_or_404(Transport, id=transport_id)
    if request.method == 'POST':
        transport_name = transport.name
        transport.delete()
        # Session-based delete success message (zh/en only)
        if request.session.get('site_language') == 'zh':
            messages.success(request, f"物流 [{transport_name}] 删除成功！")
        else:
            messages.success(request, f"Transport [{transport_name}] deleted successfully!")
    return redirect('administrator:transport_manage')

# ---------------------- News Management ----------------------
@admin_auth_required
def news_manage(request):
    """
    News list:
    - Title search
    - Category filter
    - Pagination
    """
    keyword = request.GET.get('keyword', '').strip()
    category = request.GET.get('category', '')

    news_list = News.objects.all()
    # Title search
    if keyword:
        news_list = news_list.filter(title__icontains=keyword)
    # Category filter
    if category:
        news_list = news_list.filter(category=category)

    # Pagination logic (fixed EmptyPage)
    paginator = Paginator(news_list, 3)
    page_str = request.GET.get('page', '1')
    try:
        page = int(page_str)
        if page < 1:
            page = 1
        page_news = paginator.page(page)
    except PageNotAnInteger:
        page_news = paginator.page(1)
    except EmptyPage:
        page_news = paginator.page(paginator.num_pages)

    context = {
        'news': page_news,
        'current_keyword': keyword,
        'current_category': category,
        'paginator': paginator,
        'category_choices': News.CATEGORY_CHOICES
    }
    return render(request, 'administrator/news_manage.html', context)

@admin_auth_required
def news_edit(request, news_id):
    """Edit news"""
    news = get_object_or_404(News, id=news_id)
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        category = request.POST.get('category')
        image = request.FILES.get('image')

        if not all([title, content, category]):
            messages.error(request, "Title, content and category are required!")
            return redirect('administrator:news_edit', news_id=news_id)
        # Content length verification
        if len(content) > 1000:
            messages.error(request, f"Content length cannot exceed 1000 characters (current: {len(content)})!")
            return redirect('administrator:news_edit', news_id=news_id)

        try:
            news.title = title
            news.content = content
            news.category = category
            if image:  # Update only when new image is uploaded
                news.image = image
            news.save()
            messages.success(request, f"News [{news.title}] updated successfully!")
            return redirect('administrator:news_manage')
        except Exception as e:
            messages.error(request, f"Failed to update news: {str(e)}")
            return redirect('administrator:news_edit', news_id=news_id)
    return render(request, 'administrator/news_form.html', {
        'news': news,
        'is_edit': True,
        'category_choices': News.CATEGORY_CHOICES
    })

@admin_auth_required
def news_add(request):
    """Add new news"""
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        category = request.POST.get('category')
        # Get uploaded image file
        image = request.FILES.get('image')

        # 1. Basic non-empty verification
        if not all([title, content, category]):
            messages.error(request, "Title, content and category are required!")
            return redirect('administrator:news_add')
        # 2. Content length verification (max 1000 characters)
        if len(content) > 1000:
            messages.error(request, f"Content length cannot exceed 1000 characters (current: {len(content)})!")
            return redirect('administrator:news_add')

        try:
            news = News.objects.create(
                title=title,
                content=content,
                category=category,
                user=request.user,
                image=image  # Save uploaded image
            )
            messages.success(request, f"News [{news.title}] added successfully!")
            return redirect('administrator:news_manage')
        except Exception as e:
            messages.error(request, f"Failed to add news: {str(e)}")
            return redirect('administrator:news_add')
    return render(request, 'administrator/news_form.html', {
        'is_edit': False,
        'category_choices': News.CATEGORY_CHOICES
    })

@admin_auth_required
def news_delete(request, news_id):
    """Delete news"""
    news = get_object_or_404(News, id=news_id)
    title = news.title
    news.delete()
    messages.success(request, f"News [{title}] deleted!")
    return redirect('administrator:news_manage')

# ---------------------- Company Management ----------------------
@admin_auth_required
def company_manage(request):
    """
    Company list:
    - Name search
    - Pagination
    """
    keyword = request.GET.get('keyword', '').strip()
    companies = Company.objects.all()

    # Fuzzy search by company name (case-insensitive)
    if keyword:
        companies = companies.filter(name__icontains=keyword)

    # Pagination logic (10 items per page, fixed EmptyPage error)
    paginator = Paginator(companies, 10)
    page_str = request.GET.get('page', '1')
    try:
        page = int(page_str)
        if page < 1:
            page = 1
        page_companies = paginator.page(page)
    except PageNotAnInteger:
        page_companies = paginator.page(1)
    except EmptyPage:
        page_companies = paginator.page(paginator.num_pages)

    context = {
        'companies': page_companies,
        'current_keyword': keyword,
        'paginator': paginator
    }
    return render(request, 'administrator/company_manage.html', context)


@admin_auth_required
def company_add(request):
    """Add new company (enhanced version)"""
    if request.method == 'POST':
        name = request.POST.get('name')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        contact_person = request.POST.get('contact_person', '')
        transport = request.POST.get('transport', '')
        intro = request.POST.get('intro', '')  # Company introduction
        image = request.FILES.get('image')     # Uploaded image file

        # 1. Basic verification
        if not all([name, address, phone]):
            messages.error(request, "Company name, address and phone are required!")
            return redirect('administrator:company_add')
        # 2. Company name uniqueness verification
        if Company.objects.filter(name=name).exists():
            messages.error(request, f"[{name}] already exists, do not add duplicates!")
            return redirect('administrator:company_add')
        # 3. Introduction length verification (max 500 characters)
        if len(intro) > 500:
            messages.error(request, f"Introduction length cannot exceed 500 characters (current: {len(intro)})!")
            return redirect('administrator:company_add')

        try:
            Company.objects.create(
                name=name,
                address=address,
                phone=phone,
                contact_person=contact_person,
                transport=transport,
                intro=intro,          # Save introduction
                image=image,          # Save image
                user=request.user     # Relate to current admin (optional)
            )
            messages.success(request, f"Company [{name}] added successfully!")
            return redirect('administrator:company_manage')
        except Exception as e:
            messages.error(request, f"Failed to add company: {str(e)}")
            return redirect('administrator:company_add')
    return render(request, 'administrator/company_form.html', {'is_edit': False})

@admin_auth_required
def company_edit(request, company_id):
    """Edit company (enhanced version)"""
    company = get_object_or_404(Company, id=company_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        contact_person = request.POST.get('contact_person', '')
        transport = request.POST.get('transport', '')
        intro = request.POST.get('intro', '')
        image = request.FILES.get('image')  # New uploaded image (optional)

        # Basic verification
        if not all([name, address, phone]):
            messages.error(request, "Company name, address and phone are required!")
            return redirect('administrator:company_edit', company_id=company_id)
        # Name uniqueness verification (exclude self)
        if Company.objects.filter(name=name).exclude(id=company_id).exists():
            messages.error(request, f"[{name}] already exists, do not duplicate!")
            return redirect('administrator:company_edit', company_id=company_id)
        # Introduction length verification
        if len(intro) > 500:
            messages.error(request, f"Introduction length cannot exceed 500 characters (current: {len(intro)})!")
            return redirect('administrator:company_edit', company_id=company_id)

        try:
            company.name = name
            company.address = address
            company.phone = phone
            company.contact_person = contact_person
            company.transport = transport
            company.intro = intro
            # Update only when new image is uploaded
            if image:
                company.image = image
            company.save()
            messages.success(request, f"Company [{name}] updated successfully!")
            return redirect('administrator:company_manage')
        except Exception as e:
            messages.error(request, f"Failed to update company: {str(e)}")
            return redirect('administrator:company_edit', company_id=company_id)
    return render(request, 'administrator/company_form.html', {
        'is_edit': True,
        'company': company
    })


@admin_auth_required
def company_delete(request, company_id):
    """Delete company"""
    company = get_object_or_404(Company, id=company_id)
    name = company.name
    company.delete()
    messages.success(request, f"Company [{name}] deleted!")
    return redirect('administrator:company_manage')

@admin_auth_required
def company_detail(request, company_id):
    """Company detail page: display complete information"""
    company = get_object_or_404(Company, id=company_id)
    return render(request, 'administrator/company_detail.html', {'company': company})


# ---------------------- Industry Category Management ----------------------
@admin_auth_required
def industry_manage(request):
    """
    Industry category list:
    - Search
    - Pagination
    """
    keyword = request.GET.get('keyword', '').strip()
    industries = Industry.objects.all()

    # Fuzzy search by industry name (case-insensitive)
    if keyword:
        industries = industries.filter(name__icontains=keyword)

    # Pagination logic (10 items per page)
    paginator = Paginator(industries, 10)
    page_str = request.GET.get('page', '1')
    try:
        page = int(page_str)
        if page < 1:
            page = 1
        page_industries = paginator.page(page)
    except PageNotAnInteger:
        page_industries = paginator.page(1)
    except EmptyPage:
        page_industries = paginator.page(paginator.num_pages)

    context = {
        'industries': page_industries,
        'current_keyword': keyword,
        'paginator': paginator
    }
    return render(request, 'administrator/industry_manage.html', context)

@admin_auth_required
def industry_add(request):
    """Add new industry category"""
    if request.method == 'POST':
        name = request.POST.get('name')
        desc = request.POST.get('desc', '')

        # Basic verification
        if not name:
            messages.error(request, "Industry name is required!")
            return redirect('administrator:industry_add')
        # Uniqueness verification (model has unique=True, fallback prompt)
        if Industry.objects.filter(name=name).exists():
            messages.error(request, f"Industry [{name}] already exists!")
            return redirect('administrator:industry_add')

        try:
            Industry.objects.create(name=name, desc=desc)
            messages.success(request, f"Industry [{name}] added successfully!")
            return redirect('administrator:industry_manage')
        except Exception as e:
            messages.error(request, f"Failed to add industry: {str(e)}")
            return redirect('administrator:industry_add')
    return render(request, 'administrator/industry_form.html', {'is_edit': False})

@admin_auth_required
def industry_edit(request, industry_id):
    """Edit industry category"""
    industry = get_object_or_404(Industry, id=industry_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        desc = request.POST.get('desc', '')

        if not name:
            messages.error(request, "Industry name is required!")
            return redirect('administrator:industry_edit', industry_id=industry_id)
        # Uniqueness verification (exclude self)
        if Industry.objects.filter(name=name).exclude(id=industry_id).exists():
            messages.error(request, f"Industry [{name}] already exists!")
            return redirect('administrator:industry_edit', industry_id=industry_id)

        try:
            industry.name = name
            industry.desc = desc
            industry.save()
            messages.success(request, f"Industry [{name}] updated successfully!")
            return redirect('administrator:industry_manage')
        except Exception as e:
            messages.error(request, f"Failed to update industry: {str(e)}")
            return redirect('administrator:industry_edit', industry_id=industry_id)
    return render(request, 'administrator/industry_form.html', {
        'is_edit': True,
        'industry': industry
    })

@admin_auth_required
def industry_delete(request, industry_id):
    """Delete industry category"""
    industry = get_object_or_404(Industry, id=industry_id)
    name = industry.name
    industry.delete()
    messages.success(request, f"Industry [{name}] deleted!")
    return redirect('administrator:industry_manage')


# ---------------------- Universal Delete View ----------------------
@admin_auth_required
def delete_obj(request, model, obj_id):
    """
    Universal delete view:
    - Support order/transport/news
    """
    obj_map = {
        'order': Order,
        'transport': Transport,
        'news': News,
    }
    if model not in obj_map:
        messages.error(request, "Invalid delete type!")
        return redirect('administrator:dashboard')
    obj = get_object_or_404(obj_map[model], id=obj_id)
    obj_name = obj.title if hasattr(obj, 'title') else obj.name
    obj.delete()
    messages.success(request, f"[{obj_name}] deleted successfully!")
    return redirect(f'administrator:{model}_manage')