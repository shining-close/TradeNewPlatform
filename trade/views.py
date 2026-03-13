from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from .models import Order, News, Transport  # 从当前 app 的 models.py 导入

from django.contrib.auth import get_user_model

from django.urls import reverse  # 加在文件顶部

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger  # 导入分页组件

from django.contrib import messages  # 新增这行
from django.conf import settings

from .models import Notification  # 导入通知模型

import os

# 获取当前项目的用户模型（自动适配 CustomUser）
User = get_user_model()

# 首页：无需登录
def index(request):
    # 最新3条供应订单（flag="1" 代表供应）
    supply_orders = Order.objects.filter(flag="1").order_by("-create_time")[:3]
    # 最新3条采购订单（flag="2" 代表采购）
    purchase_orders = Order.objects.filter(flag="2").order_by("-create_time")[:3]
    # 最新3条行业资讯
    latest_news = News.objects.all().order_by("-create_time")[:3]

    context = {
        "supply_orders": supply_orders,
        "purchase_orders": purchase_orders,
        "latest_news": latest_news,
    }
    return render(request, "index.html", context)

# 登录视图
def login(request):
    # 获取跳转来源（比如从发布页面跳转到登录）
    next_url = request.GET.get('next', '/')

    if request.method == 'POST':
        # 获取表单数据
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        next_url = request.POST.get('next', '/')

        # 验证用户名密码
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # 登录用户
            auth_login(request, user)

            # 记住我：设置session有效期（默认2周，勾选则30天）
            if remember:
                request.session.set_expiry(30 * 24 * 60 * 60)  # 30天
            else:
                request.session.set_expiry(0)  # 浏览器关闭即失效

            # 跳回原页面
            return redirect(next_url)
        else:
            # 登录失败：返回错误提示
            return render(request, 'accounts/login.html', {
                'error_msg': '用户名或密码错误，请重试',
                'next': next_url
            })

    # GET请求：显示登录页
    return render(request, 'accounts/login.html', {'next': next_url})


# 退出登录视图
def logout(request):
    auth_logout(request)
    return redirect('trade:index')


# 注册视图（基础版，可后续扩展）

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        if password != password2:
            return render(request, 'accounts/register.html', {'error_msg': '两次密码不一致'})
        if User.objects.filter(username=username).exists():
            return render(request, 'accounts/register.html', {'error_msg': '用户名已存在'})
        User.objects.create_user(username=username, password=password)
        return redirect('trade:login')
    return render(request, 'accounts/register.html')


@login_required
def profile(request):
    if request.method == 'POST':
        # 1. 获取基础信息
        phone = request.POST.get('phone')
        company = request.POST.get('company')
        position = request.POST.get('position')

        # 2. 处理头像上传
        if 'avatar' in request.FILES:
            # 删除旧头像（排除默认头像）
            old_avatar = request.user.avatar
            if old_avatar and not old_avatar.name.endswith('default.png'):
                old_avatar_path = os.path.join(settings.MEDIA_ROOT, str(old_avatar))
                if os.path.exists(old_avatar_path):
                    os.remove(old_avatar_path)
            # 保存新头像
            request.user.avatar = request.FILES['avatar']

        # 3. 更新用户信息
        user = request.user
        user.phone = phone
        user.company = company
        user.position = position
        user.save()

        messages.success(request, '个人信息修改成功！')
        return redirect('trade:profile')


    unread_notification_count = request.user.notifications.filter(is_read=False).count()
    # GET 请求：渲染个人中心
    return render(request, 'profile.html', {
        'user': request.user,
        'media_url': settings.MEDIA_URL,  # 传递媒体文件URL
        'unread_notification_count': unread_notification_count,  # 新增
    })


@login_required
def notification_center(request):
    # 获取当前用户的所有通知
    notifications = Notification.objects.filter(user=request.user)
    # ✅ 进入页面时，自动把所有未读通知标记为已读
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'notification_center.html', {
        'notifications': notifications
    })

# ---------------------- 订单相关（需登录） ----------------------
# 订单列表
@login_required
def order_list(request):
    flag = request.GET.get('flag', '1')
    order_list = Order.objects.filter(flag=flag).order_by('-create_time')

    # 关键：每页显示 3 条
    paginator = Paginator(order_list, 3)
    page = request.GET.get('page', 1)

    try:
        page_num = int(page)
        # 强制把页码限制在 [1, 总页数] 之间，彻底避免 page < 1 或 page 越界
        page_num = max(1, min(page_num, paginator.num_pages))
        orders = paginator.page(page_num)
    except PageNotAnInteger:
        # 页码不是数字时，默认第 1 页
        orders = paginator.page(1)
    except EmptyPage:
        # 兜底：任何 EmptyPage 都返回最后一页
        orders = paginator.page(paginator.num_pages)

    return render(request, 'order/list.html', {
        'orders': orders,
        'flag': flag
    })

# 发布订单
@login_required
def order_create(request):
    flag = request.GET.get('flag', '1')
    transports = Transport.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        category = request.POST.get('category')
        end_time = request.POST.get('end_time')
        transport_id = request.POST.get('transport')

        # 创建订单
        order = Order.objects.create(
            title=title,
            content=content,
            category=category,
            flag=flag,
            user=request.user,
            end_time=end_time if end_time else None,
            status='pending'
        )

        # 处理订单图片上传
        if 'image' in request.FILES:
            order.image = request.FILES['image']

        # 关联物流
        if transport_id:
            order.transport = Transport.objects.get(id=transport_id)

        order.save()
        messages.success(request, '订单发布成功！')
        return redirect(f"{reverse('trade:order_list')}?flag={flag}")

    return render(request, 'order/create.html', {
        'flag': flag,
        'transports': transports,
        'page_title': '发布供应信息' if flag == '1' else '发布采购需求'
    })

# 订单详情页
@login_required
def order_detail(request, order_id):
    # 获取订单，不存在则返回404
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'order/detail.html', {
        'order': order
    })


# 订单编辑页（仅限发布者修改）
@login_required
def order_edit(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # 权限校验
    if order.user != request.user:
        messages.error(request, '你没有权限修改该订单！')
        return redirect('trade:order_detail', order_id=order_id)

    transports = Transport.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        category = request.POST.get('category')
        end_time = request.POST.get('end_time')
        transport_id = request.POST.get('transport')
        status = request.POST.get('status', order.status)

        # 更新基础信息
        order.title = title
        order.content = content
        order.category = category
        order.end_time = end_time if end_time else None
        order.status = status

        # 处理图片更新（删除旧图片）
        if 'image' in request.FILES:
            # 删除旧图片（如果存在且不是空）
            if order.image and os.path.exists(os.path.join(settings.MEDIA_ROOT, str(order.image))):
                os.remove(os.path.join(settings.MEDIA_ROOT, str(order.image)))
            # 保存新图片
            order.image = request.FILES['image']

        # 关联物流
        if transport_id:
            order.transport = Transport.objects.get(id=transport_id)
        else:
            order.transport = None

        order.save()

        # ✅ 新增：创建通知记录（这行是关键！）
        Notification.objects.create(
            user=request.user,
            order=order,
            message=f"订单「{order.title}」修改成功！"
        )

        messages.success(request, '订单修改成功！')
        return redirect('trade:order_detail', order_id=order.id)

    if request.method == 'POST':
        # ... 更新订单的代码 ...
        order.save()

        # ✅ 新增：创建通知
        Notification.objects.create(
            user=request.user,
            order=order,
            message=f"订单「{order.title}」修改成功！"
        )

        messages.success(request, '订单修改成功！')
        return redirect('trade:order_detail', order_id=order.id)

    return render(request, 'order/edit.html', {
        'order': order,
        'transports': transports,
        'flag': order.flag
    })
# ---------------------- 物流相关 ----------------------
@login_required
def transport_list(request):
    from .models import Transport
    transports = Transport.objects.all()  # 从数据库获取所有物流方案
    return render(request, 'transport/list.html', {'transports': transports})

# ---------------------- 新闻相关（需登录） ----------------------
# 新闻列表
@login_required
def news_list(request):
    news = News.objects.all().order_by('-create_time')
    return render(request, 'news/list.html', {'news': news})


@login_required
def news_detail(request, news_id):
    news = get_object_or_404(News, id=news_id)
    return render(request, 'trade/news_detail.html', {'news': news})

# ---------------------- 关于我们（不需登录） ----------------------
# 关于我们页面（无需登录则去掉 @login_required 装饰器）
# @login_required  # 若允许游客访问，删除这行
def about_us(request):
    # 系统核心信息（可后续移到配置文件/数据库）
    system_info = {
        'name': '中俄贸易供需对接平台',  # 系统名称
        'address': '中国黑龙江省哈尔滨市南岗区中俄经贸大厦 15 层',  # 地址
        'phone': '400-888-9999',  # 联系电话
        'email': 'service@cn-rus-trade.com',  # 可选：邮箱
        'description': '本平台专注于中俄贸易供需信息对接，为企业提供采购、供应、物流一体化解决方案，助力中俄跨境贸易高效发展。'  # 系统简介
    }
    return render(request, 'about.html', {
        'system_info': system_info
    })

