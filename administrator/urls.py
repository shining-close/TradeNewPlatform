from django.urls import path
from . import views

# Set app namespace for template URL reverse lookup
app_name = 'administrator'

# URL routing configuration for administrator backend
# All routes are compatible with session-based language switch logic
urlpatterns = [
    # Backend dashboard (home page for administrator)
    path('', views.dashboard, name='dashboard'),

    # User management module
    path('users/', views.user_manage, name='user_manage'),
    path('users/audit/<int:user_id>/', views.user_audit, name='user_audit'),
    # New: Route for adding new user
    path('user_add/', views.user_add, name='user_add'),
    # New: Route for editing existing user
    path('user_edit/<int:user_id>/', views.user_edit, name='user_edit'),
    # New: Route for deleting user
    path('user/delete/<int:user_id>/', views.user_delete, name='user_delete'),

    # Order management module
    path('orders/', views.order_manage, name='order_manage'),
    path('orders/status/<int:order_id>/', views.order_status, name='order_status'),
    path('order_add/', views.order_add, name='order_add'),
    path('order_edit/<int:order_id>/', views.order_edit, name='order_edit'),
    path('orders/delete/<int:order_id>/', views.order_delete, name='order_delete'),

    # Transport management module
    path('transports/', views.transport_manage, name='transport_manage'),
    path('transports/add/', views.transport_add, name='transport_add'),
    path('transports/delete/<int:transport_id>/', views.transport_delete, name='transport_delete'),
    # New: Route for editing transport info
    path('transports/edit/<int:transport_id>/', views.transport_edit, name='transport_edit'),

    # News management module
    path('news_manage/', views.news_manage, name='news_manage'),
    path('news_add/', views.news_add, name='news_add'),
    path('news_edit/<int:news_id>/', views.news_edit, name='news_edit'),
    path('news_delete/<int:news_id>/', views.news_delete, name='news_delete'),

    # Core: Company management module
    path('company_manage/', views.company_manage, name='company_manage'),
    path('company_add/', views.company_add, name='company_add'),
    path('company_edit/<int:company_id>/', views.company_edit, name='company_edit'),
    path('company_delete/<int:company_id>/', views.company_delete, name='company_delete'),

    # Company detail page
    path('company_detail/<int:company_id>/', views.company_detail, name='company_detail'),

    # Industry category management module
    path('industry_manage/', views.industry_manage, name='industry_manage'),
    path('industry_add/', views.industry_add, name='industry_add'),
    path('industry_edit/<int:industry_id>/', views.industry_edit, name='industry_edit'),
    path('industry_delete/<int:industry_id>/', views.industry_delete, name='industry_delete'),

    # Universal delete route (supports multiple models)
    path('delete/<str:model>/<int:obj_id>/', views.delete_obj, name='delete_obj'),
]