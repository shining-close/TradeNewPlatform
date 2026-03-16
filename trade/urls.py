from django.urls import path
from . import views
from django.conf.urls import include

# Namespace for URL reverse resolution in templates
app_name = 'trade'

urlpatterns = [
    # Home page
    path('', views.index, name='index'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),  # Add logout function
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),  # Personal center
    path('notifications/', views.notification_center, name='notification_center'),  # Notification center

    # My orders
    path('my-orders/', views.my_orders, name='my_orders'),
    # Delete order
    path('order/delete/<int:order_id>/', views.order_delete, name='order_delete'),
    path('order/list/', views.order_list, name='order_list'),
    path('order/create/', views.order_create, name='order_create'),

    # Supply order related
    path('supply/', views.order_list, {'flag': '1'}, name='supply_list'),
    path('supply/create/', views.order_create, {'flag': '1'}, name='supply_create'),

    # Purchase order related
    path('purchase/', views.order_list, {'flag': '2'}, name='purchase_list'),
    path('purchase/create/', views.order_create, {'flag': '2'}, name='purchase_create'),

    # Order detail & edit (universal, for both supply and purchase)
    path('order/detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('order/edit/<int:order_id>/', views.order_edit, name='order_edit'),

    # Logistics list
    path('transport/', views.transport_list, name='transport_list'),
    # Logistics detail
    path('transport/detail/<int:transport_id>/', views.transport_detail, name='transport_detail'),

    # News list
    path('news/', views.news_list, name='news_list'),
    # News detail
    path('news/detail/<int:news_id>/', views.news_detail, name='news_detail'),

    # About us
    path('about/', views.about_us, name='about_us'),

    # My collections
    path('my-collections/', views.my_collections, name='my_collections'),
    # Collect / cancel collect order
    path('collect/order/<int:order_id>/', views.collect_order, name='collect_order'),
    # Collect / cancel collect news
    path('collect/news/<int:news_id>/', views.collect_news, name='collect_news'),

    # Language
    path('switch-lang/', views.switch_language, name='switch_language'),  # 新增语言切换路由
]