from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.db.models import Q  # 新增：导入Q用于模糊查询
# 新增：导入分页器
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# 新增：Django内置密码加密（用户新增时加密密码）
from django.contrib.auth.hashers import make_password

from administrator.forms import TransportAddForm
# 直接导入用户端所有模型，只读复用
from trade.models import CustomUser, Order, Company, Transport, News, Collect, Notification

# ---------------------- 核心权限控制（兼容现有CustomUser的role=admin） ----------------------
def is_admin_user(user):
    """
    双重校验：
    1. 用户已登录
    2. 是Django超级管理员 OR 自定义角色为admin
    """
    return user.is_authenticated and (user.is_superuser or user.role == "admin")

def admin_auth_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not is_admin_user(request.user):
            messages.error(request, "无管理员权限，禁止访问！")
            return redirect('trade:index')  # 重定向到用户端首页
        return view_func(request, *args, **kwargs)
    return wrapper



# ---------------------- 管理员端首页（数据看板） ----------------------
@admin_auth_required
def dashboard(request):
    """数据看板：统计平台核心数据（基于现有trade模型）"""
    data = {
        # 用户统计
        'total_users': CustomUser.objects.count(),
        'enterprise_users': CustomUser.objects.filter(role="enterprise").count(),
        'audited_enterprise': CustomUser.objects.filter(role="enterprise", is_audited=True).count(),
        # 订单统计
        'total_orders': Order.objects.count(),
        'supply_orders': Order.objects.filter(flag="1").count(),
        'demand_orders': Order.objects.filter(flag="2").count(),
        'completed_orders': Order.objects.filter(status="completed").count(),
        # 其他统计
        'total_transport': Transport.objects.count(),
        'total_news': News.objects.count(),
    }
    return render(request, 'administrator/dashboard.html', data)

# ---------------------- 用户管理 ----------------------
# 用户管理核心视图（修复分页报错）
# 用户管理核心视图（新增用户名搜索逻辑）
@admin_auth_required
def user_manage(request):
    """用户列表页：用户名搜索+角色筛选+分页（修复EmptyPage报错）"""
    # 1. 获取所有筛选/搜索参数
    role = request.GET.get('role')
    keyword = request.GET.get('keyword', '').strip()  # 用户名搜索关键字，去除首尾空格

    # 2. 基础查询 + 搜索 + 角色筛选
    users = CustomUser.objects.all().order_by('-id')
    # 用户名模糊搜索（关键字非空时生效）
    if keyword:
        users = users.filter(username__icontains=keyword)  # icontains：不区分大小写模糊匹配
    # 原有角色筛选
    if role:
        users = users.filter(role=role)

    # 3. 分页逻辑（已修复无效页码问题）
    paginator = Paginator(users, 10)
    page_str = request.GET.get('page', '1')

    try:
        page = int(page_str)
        if page < 1:
            page = 1  # 强制修正小于1的页码为1
        page_users = paginator.page(page)
    except PageNotAnInteger:
        page_users = paginator.page(1)  # 非数字页码返回第1页
    except EmptyPage:
        page_users = paginator.page(paginator.num_pages)  # 超出范围返回最后一页

    # 4. 上下文传递：新增keyword，用于搜索框回显和分页/筛选联动
    context = {
        'users': page_users,
        'current_role': role,
        'current_keyword': keyword,  # 搜索关键字回显
        'paginator': paginator
    }
    return render(request, 'administrator/user_manage.html', context)


@admin_auth_required
def user_audit(request, user_id):
    """原有企业用户审核视图（无修改，保留）"""
    user = get_object_or_404(CustomUser, id=user_id)
    if user.role == "enterprise":
        user.is_audited = not user.is_audited
        user.save()
        msg = "审核通过" if user.is_audited else "审核驳回"
        messages.success(request, f"用户{msg}成功！")
    else:
        messages.error(request, "仅企业用户可进行审核操作！")
    return redirect('administrator:user_manage')


@admin_auth_required
def user_add(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        phone = request.POST.get('phone', '')
        company = request.POST.get('company', '')
        position = request.POST.get('position', '')
        role = request.POST.get('role')
        # 同样修复布尔值转换
        is_audited = request.POST.get('is_audited') == 'on'

        if not all([username, password, role]):
            messages.error(request, "用户名、密码、角色为必填项！")
            return redirect('administrator:user_add')
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "该用户名已存在，请更换！")
            return redirect('administrator:user_add')

        try:
            user = CustomUser(
                username=username,
                password=make_password(password),
                phone=phone,
                company=company,
                position=position,
                role=role,
                is_audited=is_audited if role == "enterprise" else False
            )
            if request.FILES.get('avatar'):
                user.avatar = request.FILES.get('avatar')
            user.save()
            messages.success(request, f"用户【{username}】新增成功！")
            return redirect('administrator:user_manage')
        except Exception as e:
            messages.error(request, f"用户新增失败：{str(e)}")
            return redirect('administrator:user_add')

    context = {
        'role_choices': CustomUser.ROLE_CHOICES,
        'is_edit': False
    }
    return render(request, 'administrator/user_form.html', context)


@admin_auth_required
def user_edit(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    if user.is_superuser or user.id == request.user.id:
        messages.error(request, "禁止修改超级管理员/自身信息！")
        return redirect('administrator:user_manage')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password', '')
        phone = request.POST.get('phone', '')
        company = request.POST.get('company', '')
        position = request.POST.get('position', '')
        role = request.POST.get('role')
        # 核心修复：把复选框的 "on" 转为布尔值
        is_audited = request.POST.get('is_audited') == 'on'  # 勾选则为True，未勾选则为False

        if not all([username, role]):
            messages.error(request, "用户名、角色为必填项！")
            return redirect('administrator:user_edit', user_id=user_id)
        if CustomUser.objects.filter(username=username).exclude(id=user_id).exists():
            messages.error(request, "该用户名已存在，请更换！")
            return redirect('administrator:user_edit', user_id=user_id)

        try:
            user.username = username
            if password:
                user.password = make_password(password)
            user.phone = phone
            user.company = company
            user.position = position
            user.role = role
            # 仅企业用户时才设置审核状态，其他角色强制为False
            user.is_audited = is_audited if role == "enterprise" else False
            if request.FILES.get('avatar'):
                user.avatar = request.FILES.get('avatar')
            user.save()
            messages.success(request, f"用户【{username}】信息修改成功！")
            return redirect('administrator:user_manage')
        except Exception as e:
            messages.error(request, f"用户修改失败：{str(e)}")
            return redirect('administrator:user_edit', user_id=user_id)

    context = {
        'user': user,
        'role_choices': CustomUser.ROLE_CHOICES,
        'is_edit': True
    }
    return render(request, 'administrator/user_form.html', context)


# ---------------------- 订单管理 ----------------------
def order_manage(request):
    """订单管理：标题+用户名双搜索 + 供需/状态筛选 + 分页"""
    # 1. 获取所有筛选/搜索参数
    flag = request.GET.get('flag')
    status = request.GET.get('status')
    title_keyword = request.GET.get('title_keyword', '').strip()  # 原标题搜索
    user_keyword = request.GET.get('user_keyword', '').strip()  # 新增：用户名搜索

    # 2. 基础查询 + 多条件组合搜索
    orders = Order.objects.all().order_by('-create_time')

    # 组合搜索：标题模糊匹配 OR 用户名模糊匹配
    if title_keyword or user_keyword:
        query = Q()
        if title_keyword:
            query |= Q(title__icontains=title_keyword)  # 标题搜索
        if user_keyword:
            query |= Q(user__username__icontains=user_keyword)  # 关联用户表搜索用户名
        orders = orders.filter(query)

    # 原有供需/状态筛选
    if flag:
        orders = orders.filter(flag=flag)
    if status:
        orders = orders.filter(status=status)

    # 3. 分页逻辑（已修复EmptyPage报错）
    paginator = Paginator(orders, 10)
    page_str = request.GET.get('page', '1')
    try:
        page = int(page_str)
        if page < 1:
            page = 1
        page_orders = paginator.page(page)
    except PageNotAnInteger:
        page_orders = paginator.page(1)
    except EmptyPage:
        page_orders = paginator.page(paginator.num_pages)

    # 4. 上下文传递：新增user_keyword用于模板回显
    context = {
        'orders': page_orders,
        'current_flag': flag,
        'current_status': status,
        'current_title_keyword': title_keyword,  # 标题关键字回显
        'current_user_keyword': user_keyword,  # 用户名关键字回显
        'paginator': paginator
    }
    return render(request, 'administrator/order_manage.html', context)

@admin_auth_required
def order_status(request, order_id):
    """修改订单状态（已完成/未完成）"""
    order = get_object_or_404(Order, id=order_id)
    order.status = "completed" if order.status == "uncompleted" else "uncompleted"
    order.save()
    messages.success(request, f"订单【{order.title}】状态已更新！")
    return redirect('administrator:order_manage')


@admin_auth_required
def order_add(request):
    """新增订单：权限校验+表单处理+图片上传"""
    if request.method == 'POST':
        # 获取表单数据
        title = request.POST.get('title')
        flag = request.POST.get('flag')
        status = request.POST.get('status')
        content = request.POST.get('content')
        category = request.POST.get('category', '')
        end_time = request.POST.get('end_time')
        user_id = request.POST.get('user')
        transport_id = request.POST.get('transport')
        image_url = request.POST.get('image_url', '')

        # 非空校验
        if not all([title, flag, status, content, user_id]):
            messages.error(request, "标题、类型、状态、详情、发布人为必填项！")
            return redirect('administrator:order_add')

        try:
            # 关联用户和物流
            user = get_object_or_404(CustomUser, id=user_id)
            transport = get_object_or_404(Transport, id=transport_id) if transport_id else None

            # 创建订单对象
            order = Order(
                title=title,
                flag=flag,
                status=status,
                content=content,
                category=category,
                end_time=timezone.datetime.strptime(end_time, '%Y-%m-%dT%H:%M') if end_time else None,
                user=user,
                transport=transport,
                image_url=image_url
            )

            # 处理图片上传
            if request.FILES.get('image'):
                order.image = request.FILES.get('image')
            order.save()

            messages.success(request, "订单新增成功！")
            return redirect('administrator:order_manage')
        except Exception as e:
            messages.error(request, f"新增失败：{str(e)}")
            return redirect('administrator:order_add')

    # GET请求：渲染表单
    context = {
        'users': CustomUser.objects.all(),
        'transports': Transport.objects.all(),
        'is_edit': False
    }
    return render(request, 'administrator/order_form.html', context)


@admin_auth_required
def order_edit(request, order_id):
    """修改订单：权限校验+数据回显+保存修改"""
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        # 获取表单数据
        title = request.POST.get('title')
        flag = request.POST.get('flag')
        status = request.POST.get('status')
        content = request.POST.get('content')
        category = request.POST.get('category', '')
        end_time = request.POST.get('end_time')
        user_id = request.POST.get('user')
        transport_id = request.POST.get('transport')
        image_url = request.POST.get('image_url', '')

        # 非空校验
        if not all([title, flag, status, content, user_id]):
            messages.error(request, "标题、类型、状态、详情、发布人为必填项！")
            return redirect('administrator:order_edit', order_id=order_id)

        try:
            # 更新关联数据
            user = get_object_or_404(CustomUser, id=user_id)
            transport = get_object_or_404(Transport, id=transport_id) if transport_id else None

            # 更新订单字段
            order.title = title
            order.flag = flag
            order.status = status
            order.content = content
            order.category = category
            order.end_time = timezone.datetime.strptime(end_time, '%Y-%m-%dT%H:%M') if end_time else None
            order.user = user
            order.transport = transport
            order.image_url = image_url

            # 处理图片重新上传
            if request.FILES.get('image'):
                order.image = request.FILES.get('image')
            order.save()

            messages.success(request, "订单修改成功！")
            return redirect('administrator:order_manage')
        except Exception as e:
            messages.error(request, f"修改失败：{str(e)}")
            return redirect('administrator:order_edit', order_id=order_id)

    # GET请求：渲染表单（回显数据）
    context = {
        'order': order,
        'users': CustomUser.objects.all(),
        'transports': Transport.objects.all(),
        'is_edit': True
    }
    return render(request, 'administrator/order_form.html', context)

@admin_auth_required
def order_delete(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    title = order.title
    order.delete()
    messages.success(request, f"订单「{title}」已删除！")
    return redirect('administrator:order_manage')

# ---------------------- 物流/资讯管理（简易版） ----------------------
@admin_auth_required
def transport_add(request):
    if request.method == 'POST':
        # 关键：添加 request.FILES 接收图片
        form = TransportAddForm(request.POST, request.FILES)
        if form.is_valid():
            transport = form.save(commit=False)
            transport.user = request.user
            transport.save()
            messages.success(request, f"物流【{transport.name}】添加成功！")
            return redirect('administrator:transport_manage')
    else:
        form = TransportAddForm()
    return render(request, 'administrator/transport_add.html', {'form': form})


@admin_auth_required
def transport_manage(request):
    """物流管理：名称关键字搜索+分页（每页10条，修复EmptyPage报错）"""
    # 1. 获取搜索参数
    keyword = request.GET.get('keyword', '').strip()  # 物流名称搜索关键字

    # 2. 基础查询 + 名称模糊搜索
    transports = Transport.objects.all().order_by('-create_time')
    if keyword:
        transports = transports.filter(name__icontains=keyword)  # 不区分大小写匹配名称

    # 3. 分页逻辑（同订单/用户，兜底无效页码）
    paginator = Paginator(transports, 10)  # 每页显示10条
    page_str = request.GET.get('page', '1')
    try:
        page = int(page_str)
        if page < 1:
            page = 1  # 强制修正小于1的页码
        page_transports = paginator.page(page)
    except PageNotAnInteger:
        page_transports = paginator.page(1)
    except EmptyPage:
        page_transports = paginator.page(paginator.num_pages)

    # 4. 上下文传递（搜索关键字+分页数据）
    context = {
        'transports': page_transports,
        'current_keyword': keyword,
        'paginator': paginator
    }
    return render(request, 'administrator/transport_manage.html', context)

@admin_auth_required
def transport_delete(request, transport_id):
    transport = get_object_or_404(Transport, id=transport_id)
    transport.delete()
    messages.success(request, f"物流【{transport.name}】已删除！")
    return redirect('administrator:transport_manage')


@admin_auth_required
def transport_edit(request, transport_id):
    """管理员修改物流信息"""
    transport = get_object_or_404(Transport, id=transport_id)

    if request.method == 'POST':
        # ✅ 关键：添加 request.FILES 接收上传的图片
        form = TransportAddForm(request.POST, request.FILES, instance=transport)
        if form.is_valid():
            form.save()
            messages.success(request, f"物流【{transport.name}】修改成功！")
            return redirect('administrator:transport_manage')  # 跳回列表
    else:
        # GET请求：展示现有数据（自动填充表单）
        form = TransportAddForm(instance=transport)

    return render(request, 'administrator/transport_edit.html', {
        'form': form,
        'transport': transport  # 传递物流信息到模板
    })


# ---------------------- 资讯管理----------------------

@admin_auth_required
def news_manage(request):
    """资讯列表：标题搜索+分类筛选+分页"""
    keyword = request.GET.get('keyword', '').strip()
    category = request.GET.get('category', '')

    news_list = News.objects.all()
    # 标题搜索
    if keyword:
        news_list = news_list.filter(title__icontains=keyword)
    # 分类筛选
    if category:
        news_list = news_list.filter(category=category)

    # 分页逻辑（修复EmptyPage）
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
    news = get_object_or_404(News, id=news_id)
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        category = request.POST.get('category')
        image = request.FILES.get('image')

        if not all([title, content, category]):
            messages.error(request, "标题、内容、分类为必填项！")
            return redirect('administrator:news_edit', news_id=news_id)
        # 内容字数限制校验
        if len(content) > 1000:
            messages.error(request, f"内容字数不能超过1000字，当前为{len(content)}字！")
            return redirect('administrator:news_edit', news_id=news_id)

        try:
            news.title = title
            news.content = content
            news.category = category
            if image:  # 仅当有新图片上传时才更新
                news.image = image
            news.save()
            messages.success(request, f"资讯「{news.title}」修改成功！")
            return redirect('administrator:news_manage')
        except Exception as e:
            messages.error(request, f"修改失败：{str(e)}")
            return redirect('administrator:news_edit', news_id=news_id)
    return render(request, 'administrator/news_form.html', {
        'news': news,
        'is_edit': True,
        'category_choices': News.CATEGORY_CHOICES
    })

@admin_auth_required
def news_add(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        category = request.POST.get('category')
        # 获取上传的图片文件
        image = request.FILES.get('image')

        # 1. 基础非空校验
        if not all([title, content, category]):
            messages.error(request, "标题、内容、分类为必填项！")
            return redirect('administrator:news_add')
        # 2. 内容字数限制校验（1000字以内）
        if len(content) > 1000:
            messages.error(request, f"内容字数不能超过1000字，当前为{len(content)}字！")
            return redirect('administrator:news_add')

        try:
            news = News.objects.create(
                title=title,
                content=content,
                category=category,
                user=request.user,
                image=image  # 保存上传的图片
            )
            messages.success(request, f"资讯「{news.title}」新增成功！")
            return redirect('administrator:news_manage')
        except Exception as e:
            messages.error(request, f"新增失败：{str(e)}")
            return redirect('administrator:news_add')
    return render(request, 'administrator/news_form.html', {
        'is_edit': False,
        'category_choices': News.CATEGORY_CHOICES
    })

@admin_auth_required
def news_delete(request, news_id):
    """删除资讯"""
    news = get_object_or_404(News, id=news_id)
    title = news.title
    news.delete()
    messages.success(request, f"资讯「{title}」已删除！")
    return redirect('administrator:news_manage')

# ---------------------- 公司 ----------------------

@admin_auth_required
def company_manage(request):
    """公司列表：名称搜索 + 分页"""
    keyword = request.GET.get('keyword', '').strip()
    companies = Company.objects.all()

    # 按公司名称模糊搜索（不区分大小写）
    if keyword:
        companies = companies.filter(name__icontains=keyword)

    # 分页逻辑（每页10条，修复EmptyPage报错）
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


# ========== 新增公司（升级） ==========
@admin_auth_required
def company_add(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        contact_person = request.POST.get('contact_person', '')
        transport = request.POST.get('transport', '')
        intro = request.POST.get('intro', '')  # 公司简介
        image = request.FILES.get('image')     # 上传的图片文件

        # 1. 基础校验
        if not all([name, address, phone]):
            messages.error(request, "公司名称、地址、联系电话为必填项！")
            return redirect('administrator:company_add')
        # 2. 公司名称唯一性校验
        if Company.objects.filter(name=name).exists():
            messages.error(request, f"「{name}」已存在，请勿重复添加！")
            return redirect('administrator:company_add')
        # 3. 公司简介字数校验（500字限制）
        if len(intro) > 500:
            messages.error(request, f"公司简介字数不能超过500字，当前输入{len(intro)}字！")
            return redirect('administrator:company_add')

        try:
            Company.objects.create(
                name=name,
                address=address,
                phone=phone,
                contact_person=contact_person,
                transport=transport,
                intro=intro,          # 保存简介
                image=image,          # 保存图片
                user=request.user     # 关联当前管理员（可选）
            )
            messages.success(request, f"公司「{name}」新增成功！")
            return redirect('administrator:company_manage')
        except Exception as e:
            messages.error(request, f"新增失败：{str(e)}")
            return redirect('administrator:company_add')
    return render(request, 'administrator/company_form.html', {'is_edit': False})

# ========== 修改公司（升级） ==========
@admin_auth_required
def company_edit(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        contact_person = request.POST.get('contact_person', '')
        transport = request.POST.get('transport', '')
        intro = request.POST.get('intro', '')
        image = request.FILES.get('image')  # 新上传的图片（可选）

        # 基础校验
        if not all([name, address, phone]):
            messages.error(request, "公司名称、地址、联系电话为必填项！")
            return redirect('administrator:company_edit', company_id=company_id)
        # 名称唯一性校验（排除自身）
        if Company.objects.filter(name=name).exclude(id=company_id).exists():
            messages.error(request, f"「{name}」已存在，请勿重复！")
            return redirect('administrator:company_edit', company_id=company_id)
        # 简介字数校验
        if len(intro) > 500:
            messages.error(request, f"公司简介字数不能超过500字，当前输入{len(intro)}字！")
            return redirect('administrator:company_edit', company_id=company_id)

        try:
            company.name = name
            company.address = address
            company.phone = phone
            company.contact_person = contact_person
            company.transport = transport
            company.intro = intro
            # 只有上传新图片时才更新
            if image:
                company.image = image
            company.save()
            messages.success(request, f"公司「{name}」修改成功！")
            return redirect('administrator:company_manage')
        except Exception as e:
            messages.error(request, f"修改失败：{str(e)}")
            return redirect('administrator:company_edit', company_id=company_id)
    return render(request, 'administrator/company_form.html', {
        'is_edit': True,
        'company': company
    })


@admin_auth_required
def company_delete(request, company_id):
    """删除公司"""
    company = get_object_or_404(Company, id=company_id)
    name = company.name
    company.delete()
    messages.success(request, f"公司「{name}」已删除！")
    return redirect('administrator:company_manage')

@admin_auth_required
def company_detail(request, company_id):
    """公司详情页：展示完整信息"""
    company = get_object_or_404(Company, id=company_id)
    return render(request, 'administrator/company_detail.html', {'company': company})

# ---------------------- 通用删除视图 ----------------------
@admin_auth_required
def delete_obj(request, model, obj_id):
    """通用删除：支持订单/物流/资讯"""
    obj_map = {
        'order': Order,
        'transport': Transport,
        'news': News,
    }
    if model not in obj_map:
        messages.error(request, "无效删除类型！")
        return redirect('administrator:dashboard')
    obj = get_object_or_404(obj_map[model], id=obj_id)
    obj_name = obj.title if hasattr(obj, 'title') else obj.name
    obj.delete()
    messages.success(request, f"【{obj_name}】已成功删除！")
    return redirect(f'administrator:{model}_manage')