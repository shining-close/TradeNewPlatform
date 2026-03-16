跨境贸易服务平台项目 README

项目简介
本项目是基于 Django 框架开发的跨境贸易服务平台，支持多角色（游客、企业用户、管理员）权限管理，
实现了订单发布 / 管理 / 收藏、企业信息管理、物流管理、管理员后台等核心业务功能。

运行环境要求
Python 3.10+
Django 6.0.3
MySQL 8.0+（或兼容的数据库）

快速启动步骤
1. 克隆 / 下载项目
将项目代码解压到本地目录，进入项目根目录：
cd TradePlatformProject

2. 安装依赖
执行以下命令安装项目所需依赖包：
pip install -r requirements.txt

3. 数据库配置
在 TradePlatform/settings.py 中配置你的 MySQL 数据库连接信息：
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': '你的数据库名',
        'USER': '你的数据库用户名',
        'PASSWORD': '你的数据库密码',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}

4. 数据库迁移
执行以下命令创建数据库表结构：
python manage.py makemigrations
python manage.py migrate

5. 创建超级管理员
按提示输入用户名、邮箱和密码，用于登录管理员后台。
python manage.py createsuperuser

6. 启动项目 
启动成功后，访问地址：http://127.0.0.1:8000/
python manage.py runserver

测试账号（用于功能验证）
管理员	admin	Admin123456	 管理所有用户、订单、物流数据
企业用户	test_ent	Test123456	发布 / 编辑 / 查看 / 收藏自身订单
游客	test_visitor	Test123456	浏览订单列表，需登录后才能操作
核心功能说明
多角色权限控制：游客、企业用户、管理员权限严格隔离
订单管理：企业用户可发布供应 / 采购订单，管理员可修改订单状态、删除订单
收藏功能：企业用户可收藏感兴趣的订单，同一订单不可重复收藏
企业管理：企业用户可维护自身企业信息，管理员可查看所有企业信息
物流管理：管理员可维护物流线路信息，企业用户发布订单时可选择物流方式

项目结构
TradePlatformProject/
├── trade/                  # 核心业务应用
│   ├── models.py           # 数据模型（用户、企业、订单、收藏等）
│   ├── views.py            # 业务视图
│   ├── urls.py             # 路由配置
│   └── tests.py            # 单元测试代码
├── administrator/          # 管理员后台应用
│   ├── views.py            # 后台管理视图
│   ├── urls.py             # 后台路由配置
│   └── tests.py            # 后台单元测试
├── TradePlatform/          # 项目配置
│   ├── settings.py         # 全局配置（数据库、静态文件等）
│   └── urls.py             # 根路由配置
├── requirements.txt        # 项目依赖清单
├── manage.py               # Django 管理脚本
└── README.md               # 项目说明文档

单元测试说明
项目包含 29 个单元测试用例，覆盖核心模型与业务逻辑，执行以下命令运行所有测试：
测试通过后会显示：OK，代表所有用例验证通过。
python manage.py test trade administrator

注意事项
确保本地已安装并启动 MySQL 服务，数据库配置与 settings.py 一致
若需使用图片上传功能，需确保 media/ 目录有写入权限
首次运行需执行数据库迁移命令，否则会出现表不存在的错误