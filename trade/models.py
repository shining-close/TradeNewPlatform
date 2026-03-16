from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _  # Import transform

# Custom user model (core)
class CustomUser(AbstractUser):
    """Extend Django's built-in user model to adapt to user roles and info of cross-border trade platform"""
    ROLE_CHOICES = (
        ("visitor", _("Visitor")),
        ("enterprise", _("Enterprise User")),
        ("admin", _("Administrator")),
    )
    phone = models.CharField(max_length=20, verbose_name=_("Phone Number"), blank=True, null=True)
    company = models.CharField(max_length=100, verbose_name=_("Affiliated Company"), blank=True, null=True)
    position = models.CharField(max_length=50, verbose_name=_("Position"), blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="visitor", verbose_name=_("User Role"))
    is_audited = models.BooleanField(default=False, verbose_name=_("Audited Status"))  # Enterprise user audit mark
    nationality = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("Nationality"))
    avatar = models.ImageField(
        upload_to='avatars/',  # Avatar storage path: media/avatars/
        default='avatars/default.png',  # Default avatar
        blank=True,  # Allow empty
        verbose_name=_("User Avatar")
    )

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        db_table = "trade_user"  # Specify database table name

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    # Resolve reverse accessor conflict
    groups = models.ManyToManyField(
        Group,
        verbose_name=_("Groups"),
        blank=True,
        help_text=_("The groups this user belongs to. A user will get all permissions granted to each of their groups."),
        related_name="custom_user_set",
        related_query_name="custom_user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_("User Permissions"),
        blank=True,
        help_text=_("Specific permissions for this user."),
        related_name="custom_user_set",
        related_query_name="custom_user",
    )

# Company information model
class Company(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Company Name"))
    address = models.CharField(max_length=200, verbose_name=_("Company Address"))
    phone = models.CharField(max_length=20, verbose_name=_("Company Phone"))
    transport = models.CharField(max_length=100, verbose_name=_("Cooperative Logistics"), blank=True, null=True)
    contact_person = models.CharField(max_length=50, verbose_name=_("Contact Person"), blank=True, null=True)
    # Add: Company introduction (500 words limit)
    intro = models.TextField(max_length=500, verbose_name=_("Company Introduction"), blank=True, null=True)
    # Add: Company image (support upload)
    image = models.ImageField(
        upload_to='company_images/',  # Save to media/company_images/
        verbose_name=_("Company Image"),
        blank=True,
        null=True
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name=_("Associated User"),
        related_name="companies",
        null=True,  # Allow empty (pure company management scenario)
        blank=True
    )

    class Meta:
        verbose_name = _("Company")
        verbose_name_plural = _("Companies")
        db_table = "trade_company"

    def __str__(self):
        return self.name

# Logistics information model
class Transport(models.Model):
    # Logistics type options (corresponding to front-end drop-down box value)
    TYPE_CHOICES = (
        ('air', _("Air Transport")),
        ('sea', _("Sea Transport")),
        ('land', _("Land Transport")),
    )
    name = models.CharField(max_length=100, verbose_name=_("Logistics Name"))
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name=_("Logistics Type"))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Reference Price (CNY/Unit)"), default=0.00)
    time = models.CharField(max_length=50, verbose_name=_("Transport Time Limit"), default="7-15 days")
    company = models.CharField(max_length=100, verbose_name=_("Logistics Company"), blank=True, null=True)
    description = models.TextField(verbose_name=_("Logistics Description"), blank=True, null=True)
    image = models.ImageField(upload_to="transport/images/", blank=True, null=True, verbose_name=_("Logistics Image"))
    create_time = models.DateTimeField(auto_now_add=True, verbose_name=_("Creation Time"))
    update_time = models.DateTimeField(auto_now=True, verbose_name=_("Update Time"))

    class Meta:
        verbose_name = _("International Logistics")
        verbose_name_plural = _("International Logistics")
        ordering = ["-create_time"]

    def __str__(self):
        return f"{self.type} - {self.name}"

# News and information model
class News(models.Model):
    """Cross-border trade related news"""
    CATEGORY_CHOICES = (
        ("policy", _("Policy")),
        ("market", _("Market")),
        ("logistics", _("Logistics")),
    )
    title = models.CharField(max_length=200, verbose_name=_("Title"))
    content = models.TextField(verbose_name=_("Content"))
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name=_("Category"))
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name=_("Publisher"), related_name="news")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name=_("Publish Time"))
    image = models.ImageField(
        upload_to='news_images/',  # Upload to media/news_images/
        verbose_name=_("Cover Image"),
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = _("News")
        verbose_name_plural = _("News")
        db_table = "trade_news"
        ordering = ["-create_time"]  # Sort by publish time in reverse order

    def __str__(self):
        return self.title

class Industry(models.Model):
    """Common industry categories for China-Russia trade"""
    name = models.CharField(max_length=50, verbose_name=_("Industry Name"), unique=True)
    desc = models.CharField(max_length=200, blank=True, null=True, verbose_name=_("Industry Description"))
    create_time = models.DateTimeField(auto_now_add=True, verbose_name=_("Creation Time"))

    class Meta:
        verbose_name = _("Industry Category")
        verbose_name_plural = _("Industry Categories")
        ordering = ["name"]

    def __str__(self):
        return self.name

    @classmethod
    def init_default_categories(cls):
        default_categories = [
            {"name": _("Agricultural Products"), "desc": _("Grain, fruits and vegetables, meat, aquatic products and other agricultural, forestry, animal husbandry and fishery products")},
            {"name": _("Energy and Minerals"), "desc": _("Petroleum, natural gas, coal, metal minerals, etc.")},
            {"name": _("Mechanical Equipment"), "desc": _("Engineering machinery, machine tools, agricultural machinery, heavy equipment, etc.")},
            {"name": _("Electronic Products"), "desc": _("Consumer electronics, electronic components, communication equipment, etc.")},
            {"name": _("Chemical Raw Materials"), "desc": _("Basic chemicals, fine chemicals, chemical products, etc.")},
            {"name": _("Light Industry and Textiles"), "desc": _("Clothing, home textiles, furniture, daily necessities, etc.")},
            {"name": _("Automobiles and Parts"), "desc": _("Vehicles, auto parts, maintenance parts, etc.")},
            {"name": _("Building Materials"), "desc": _("Steel, cement, glass, decorative materials, etc.")},
            {"name": _("Pharmaceutical and Health"), "desc": _("API, medical devices, health products, etc.")},
            {"name": _("Logistics Services"), "desc": _("International transportation, warehousing, customs clearance and other supporting services")},
            {"name": _("Other Industries"), "desc": _("Unclassified other trade categories")}
        ]
        for item in default_categories:
            cls.objects.get_or_create(name=item["name"], defaults=item)

# Modify Order model: associate industry category (replace original category field)
class Order(models.Model):
    flag_choices = (
        ("1", _("Supply")),
        ("2", _("Purchase")),
    )
    status_choices = (
        ("uncompleted", _("Uncompleted")),
        ("completed", _("Completed")),
    )
    title = models.CharField(max_length=100, verbose_name=_("Order Title"))
    industry = models.ForeignKey(Industry, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Industry Category"))
    content = models.TextField(verbose_name=_("Order Details"))
    end_time = models.DateTimeField(blank=True, null=True, verbose_name=_("Deadline"))
    flag = models.CharField(max_length=1, choices=flag_choices, verbose_name=_("Order Type"))
    status = models.CharField(max_length=20, choices=status_choices, default="uncompleted", verbose_name=_("Order Status"))
    # Fixed user foreign key (use string reference to avoid NameError)
    user = models.ForeignKey('trade.CustomUser', on_delete=models.CASCADE, verbose_name=_("Publisher"))
    # Add: Contact phone + Nationality (optional fields, no impact on existing data)
    contact_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name=_("Contact Phone"))
    nationality = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("Nationality"))
    transport = models.ForeignKey(Transport, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Associated Logistics"))
    image = models.ImageField(upload_to='order_images/', blank=True, null=True, verbose_name=_("Local Image"))
    image_url = models.URLField(verbose_name=_("Online Image URL"), blank=True, null=True)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name=_("Creation Time"))
    update_time = models.DateTimeField(auto_now=True, verbose_name=_("Update Time"))

    class Meta:
        verbose_name = _("Trade Order")
        verbose_name_plural = _("Trade Orders")
        ordering = ["-create_time"]

    def __str__(self):
        return f"{self.get_flag_display()}-{self.title}"

class Collect(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name=_("Collector"))
    order = models.ForeignKey(Order, on_delete=models.CASCADE, blank=True, null=True, verbose_name=_("Collected Order"))
    news = models.ForeignKey(News, on_delete=models.CASCADE, blank=True, null=True, verbose_name=_("Collected News"))
    create_time = models.DateTimeField(auto_now_add=True, verbose_name=_("Collection Time"))

    class Meta:
        verbose_name = _("Collection")
        verbose_name_plural = _("Collections")
        # Unique constraint: the same user cannot collect the same order/news repeatedly
        unique_together = [
            ['user', 'order'],  # A user can collect the same order only once
            ['user', 'news']    # A user can collect the same news only once
        ]

    def __str__(self):
        if self.order:
            return f"{self.user.username} {_('collected order')}: {self.order.title}"
        elif self.news:
            return f"{self.user.username} {_('collected news')}: {self.news.title}"
        return f"{self.user.username}'s {_('Collections')}"

class Notification(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='notifications',
        verbose_name=_("Recipient")
    )
    # Modify this part: allow order to be empty, set to null when deleted
    order = models.ForeignKey(
        Order, on_delete=models.SET_NULL,
        related_name='notifications',
        verbose_name=_("Associated Order"),
        null=True,
        blank=True
    )
    message = models.CharField(max_length=255, verbose_name=_("Notification Content"))
    is_read = models.BooleanField(default=False, verbose_name=_("Read Status"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Creation Time"))

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ['-created_at']  # Sort by time in reverse order

    def __str__(self):
        return f"{self.user.username} - {self.message}"