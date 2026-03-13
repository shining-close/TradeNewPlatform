from django.urls import path
from . import views

# 命名空间，方便模板中反向解析URL
app_name = 'trade'

urlpatterns = [
    # 首页
    path('', views.index, name='index'),


    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),  # 新增退出登录
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),  # 个人中心
    path('notifications/', views.notification_center, name='notification_center'),  # 通知中心





    path('order/list/', views.order_list, name='order_list'),
    path('order/create/', views.order_create, name='order_create'),
    # 新增：订单详情（接收订单ID）
    path('order/detail/<int:order_id>/', views.order_detail, name='order_detail'),
    # 新增：订单编辑（接收订单ID）
    path('order/edit/<int:order_id>/', views.order_edit, name='order_edit'),


    path('transport/list/', views.transport_list, name='transport_list'),


    path('news/list/', views.news_list, name='news_list'),
    path('news/<int:news_id>/', views.news_detail, name='news_detail'),

    path('about/', views.about_us, name='about_us'),  # 新增：关于我们

]