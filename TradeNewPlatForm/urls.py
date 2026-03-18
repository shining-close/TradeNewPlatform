"""
URL configuration for TradeNewPlatForm project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""


from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
import os

urlpatterns = [
    # 1. Django 自带后台 (建议保留默认路径或确保拼写正确)
    path('django-admin/', admin.site.urls),

    # 2. 你的业务应用路由
    # 将 trade 设为 '' (空字符串)，这样访问域名直接进入首页，解决本地找不到页面的问题
    path('', include('trade.urls')),

    # 3. 管理员后端入口
    path('admin/', include('administrator.urls')),
]

# --- 核心修复部分：处理静态文件和媒体文件 ---

# 方案 A：标准的 Django 开发环境配置 (仅在 DEBUG=True 时生效)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# 方案 B：生产环境强制补丁 (关键！)
# 无论 DEBUG 是 True 还是 False，这段代码都会运行。
# 它强制让 Django 接管 /media/ 和 /static/ 路径，解决 Render 线上图片 404 的问题。
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]