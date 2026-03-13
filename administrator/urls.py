from django.urls import path
from . import views

app_name = 'administrator'  # 独立命名空间

urlpatterns = [
    # 首页
    path('', views.dashboard, name='dashboard'),



    # 用户管理
    path('users/', views.user_manage, name='user_manage'),
    path('users/audit/<int:user_id>/', views.user_audit, name='user_audit'),
    # 新增：用户新增、修改路由
    path('user_add/', views.user_add, name='user_add'),
    path('user_edit/<int:user_id>/', views.user_edit, name='user_edit'),



    # 订单管理
    path('orders/', views.order_manage, name='order_manage'),
    path('orders/status/<int:order_id>/', views.order_status, name='order_status'),
    path('order_add/', views.order_add, name='order_add'),
    path('order_edit/<int:order_id>/', views.order_edit, name='order_edit'),
    path('orders/delete/<int:order_id>/', views.order_delete, name='order_delete'),



    # 物流管理
    path('transports/', views.transport_manage, name='transport_manage'),
    path('transports/add/', views.transport_add, name='transport_add'),
    path('transports/delete/<int:transport_id>/', views.transport_delete, name='transport_delete'),
    path('transports/edit/<int:transport_id>/', views.transport_edit, name='transport_edit'),  # 新增编辑路由


    # /资讯管理
    path('news_manage/', views.news_manage, name='news_manage'),
    path('news_add/', views.news_add, name='news_add'),
    path('news_edit/<int:news_id>/', views.news_edit, name='news_edit'),
    path('news_delete/<int:news_id>/', views.news_delete, name='news_delete'),

    # 公司管理核心路由
    path('company_manage/', views.company_manage, name='company_manage'),
    path('company_add/', views.company_add, name='company_add'),
    path('company_edit/<int:company_id>/', views.company_edit, name='company_edit'),
    path('company_delete/<int:company_id>/', views.company_delete, name='company_delete'),
    # 公司详情页
    path('company_detail/<int:company_id>/', views.company_detail, name='company_detail'),

    # 通用删除
    path('delete/<str:model>/<int:obj_id>/', views.delete_obj, name='delete_obj'),
]