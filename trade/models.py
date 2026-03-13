from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone

# 自定义用户模型（核心）
class CustomUser(AbstractUser):
    """扩展Django自带用户模型，适配跨境贸易平台的用户角色和信息"""
    ROLE_CHOICES = (
        ("visitor", "游客"),
        ("enterprise", "企业用户"),
        ("admin", "管理员"),
    )
    phone = models.CharField(max_length=20, verbose_name="手机号", blank=True, null=True)
    company = models.CharField(max_length=100, verbose_name="所属公司", blank=True, null=True)
    position = models.CharField(max_length=50, verbose_name="职位", blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="visitor", verbose_name="角色")
    is_audited = models.BooleanField(default=False, verbose_name="是否审核通过")  # 企业用户审核标记

    avatar = models.ImageField(
        upload_to='avatars/',  # 头像存储路径：media/avatars/
        default='avatars/default.png',  # 默认头像
        blank=True,  # 允许为空
        verbose_name='用户头像'
    )

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"
        db_table = "trade_user"  # 指定数据库表名

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    # 解决反向访问器冲突
    groups = models.ManyToManyField(
        Group,
        verbose_name="groups",
        blank=True,
        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
        related_name="custom_user_set",  # 新增：修改反向关联名
        related_query_name="custom_user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name="user permissions",
        blank=True,
        help_text="Specific permissions for this user.",
        related_name="custom_user_set",  # 新增：修改反向关联名
        related_query_name="custom_user",
    )

# 公司信息模型
class Company(models.Model):
    name = models.CharField(max_length=100, verbose_name="公司名称")
    address = models.CharField(max_length=200, verbose_name="公司地址")
    phone = models.CharField(max_length=20, verbose_name="公司电话")
    transport = models.CharField(max_length=100, verbose_name="合作物流", blank=True, null=True)
    contact_person = models.CharField(max_length=50, verbose_name="联系人", blank=True, null=True)
    # 新增：公司简介（500字限制）
    intro = models.TextField(max_length=500, verbose_name="公司简介", blank=True, null=True)
    # 新增：公司图片（支持上传）
    image = models.ImageField(
        upload_to='company_images/',  # 图片保存到 media/company_images/ 目录
        verbose_name="公司图片",
        blank=True,
        null=True
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name="关联用户",
        related_name="companies",
        null=True,  # 允许为空（纯公司管理场景）
        blank=True
    )

    class Meta:
        verbose_name = "公司"
        verbose_name_plural = "公司"
        db_table = "trade_company"

    def __str__(self):
        return self.name

# 物流信息模型
class Transport(models.Model):
    """国际物流服务信息"""
    name = models.CharField(max_length=100, verbose_name="物流名称")
    type = models.CharField(max_length=50, verbose_name="物流类型", blank=True, null=True)  # 海运/空运/陆运
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="参考价格", blank=True, null=True)
    time = models.CharField(max_length=50, verbose_name="时效", blank=True, null=True)  # 如"7-10天"
    company = models.CharField(max_length=100, verbose_name="物流公司", blank=True, null=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="录入用户", related_name="transports")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    # 新增字段
    description = models.TextField(blank=True, null=True, verbose_name='物流描述')  # 描述字段
    image = models.ImageField(upload_to='transport/', blank=True, null=True, verbose_name='物流图片')  # 图片字段，保存到media/transport/

    class Meta:
        verbose_name = "物流"
        verbose_name_plural = "物流"
        db_table = "trade_transport"

    def __str__(self):
        return self.name

# 新闻资讯模型
class News(models.Model):
    """跨境贸易相关新闻"""
    CATEGORY_CHOICES = (
        ("policy", "政策"),
        ("market", "市场"),
        ("logistics", "物流"),
    )
    title = models.CharField(max_length=200, verbose_name="标题")
    content = models.TextField(verbose_name="内容")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="分类")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="发布用户", related_name="news")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="发布时间")

    image = models.ImageField(
        upload_to='news_images/',  # 上传到 media/news_images/ 目录
        verbose_name="封面图",
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = "新闻"
        verbose_name_plural = "新闻"
        db_table = "trade_news"
        ordering = ["-create_time"]  # 按发布时间倒序

    def __str__(self):
        return self.title

# 订单模型（供需订单）
class Order(models.Model):
    """跨境贸易供需订单"""
    FLAG_CHOICES = (
        ("1", "供应"),
        ("2", "需求"),
    )
    STATUS_CHOICES = (
        ("completed", "已完成"),
        ("uncompleted", "未完成"),
    )
    title = models.CharField(max_length=200, verbose_name="订单标题")
    content = models.TextField(verbose_name="订单详情")
    flag = models.CharField(max_length=10, choices=FLAG_CHOICES, verbose_name="供需类型")
    category = models.CharField(max_length=50, verbose_name="行业分类", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="uncompleted", verbose_name="订单状态")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    end_time = models.DateTimeField(verbose_name="截止时间", blank=True, null=True)
    image_url = models.URLField(verbose_name="图片URL", blank=True, null=True)
    transport = models.ForeignKey(Transport, on_delete=models.SET_NULL, verbose_name="关联物流", blank=True, null=True, related_name="orders")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="发布用户", related_name="orders")

    image = models.ImageField(
        upload_to='order_images/',  # 订单图片存储路径：media/order_images/
        blank=True,  # 允许为空（可选上传）
        null=True,
        verbose_name='订单图片'
    )

    class Meta:
        verbose_name = "订单"
        verbose_name_plural = "订单"
        db_table = "trade_order"
        ordering = ["-create_time"]

    def __str__(self):
        return f"{self.get_flag_display()} - {self.title}"

# 收藏模型（用户收藏订单/新闻）
class Collect(models.Model):
    """用户收藏表，关联用户与订单/新闻"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="用户", related_name="collects")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name="订单", blank=True, null=True, related_name="collectors")
    news = models.ForeignKey(News, on_delete=models.CASCADE, verbose_name="新闻", blank=True, null=True, related_name="collectors")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="收藏时间")

    class Meta:
        verbose_name = "收藏"
        verbose_name_plural = "收藏"
        db_table = "trade_collect"
        # 防止重复收藏：一个用户对同一个订单/新闻只能收藏一次
        unique_together = [
            ["user", "order"],
            ["user", "news"],
        ]

    def __str__(self):
        if self.order:
            return f"{self.user.username} 收藏 {self.order.title}"
        elif self.news:
            return f"{self.user.username} 收藏 {self.news.title}"
        return f"{self.user.username} 的收藏"

class Notification(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='notifications',
        verbose_name='接收用户'
    )
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='notifications',
        verbose_name='关联订单'
    )
    message = models.CharField(max_length=255, verbose_name='通知内容')
    is_read = models.BooleanField(default=False, verbose_name='是否已读')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '通知'
        verbose_name_plural = '通知'
        ordering = ['-created_at']  # 按时间倒序，最新的在最上面

    def __str__(self):
        return f"{self.user.username} - {self.message}"