from django.db import models
from django.utils import timezone
from apps.auth_app.models import User

class SystemSettings(models.Model):
    """System-wide configuration settings - SUPER ADMIN ONLY"""
    
    # 1. GLOBAL FEATURE CONTROL
    enable_pos_billing = models.BooleanField(default=True)
    enable_inventory = models.BooleanField(default=True)
    enable_gst_tax = models.BooleanField(default=True)
    enable_loyalty_points = models.BooleanField(default=True)
    enable_stock_alerts = models.BooleanField(default=True)
    enable_invoice_pdf = models.BooleanField(default=True)
    enable_sms_notifications = models.BooleanField(default=True)
    enable_sms_notifications = models.BooleanField(default=True)
    enable_email_notifications = models.BooleanField(default=True)
    enable_discounts = models.BooleanField(default=True, help_text="Global switch for discount module")
    
    # 1.0 DASHBOARD FEATURE CONTROL (OWNER DASHBOARD)
    dashboard_access_enable = models.BooleanField(default=True, help_text="Enable/Disable owner dashboard completely")
    
    # 1.1 Dashboard KPI Cards
    dashboard_total_customers_card = models.BooleanField(default=True, help_text="Show Total Customers card")
    dashboard_total_products_card = models.BooleanField(default=True, help_text="Show Total Products card")
    dashboard_total_revenue_card = models.BooleanField(default=True, help_text="Show Total Revenue card")
    dashboard_active_customers_card = models.BooleanField(default=True, help_text="Show Active Customers card")
    
    # 1.2 Revenue Safety Control
    dashboard_revenue_visibility = models.BooleanField(default=True, help_text="Show revenue amounts (prevents showing ₹ for trial/restricted)")
    
    # 1.3 Recent Orders Section
    dashboard_recent_orders_widget = models.BooleanField(default=True, help_text="Show Recent Orders section")
    dashboard_invoice_number_visibility = models.BooleanField(default=True, help_text="Show Invoice numbers in orders")
    dashboard_order_amount_visibility = models.BooleanField(default=True, help_text="Show order amounts")
    dashboard_order_status_visibility = models.BooleanField(default=True, help_text="Show order status")
    
    # 1.4 Quick Action Buttons
    dashboard_create_invoice_button = models.BooleanField(default=True, help_text="Show Create Invoice button")
    dashboard_add_product_button = models.BooleanField(default=True, help_text="Show Add Product button")
    dashboard_add_customer_button = models.BooleanField(default=True, help_text="Show Add Customer button")
    
    # 1.5 Notification & Data Control
    dashboard_notification_bell = models.BooleanField(default=True, help_text="Show notification bell for alerts")
    dashboard_data_calculation_enable = models.BooleanField(default=True, help_text="Calculate and show dashboard numbers (safe mode if disabled)")

    # 1.1 DISCOUNT RULES (SUPER ADMIN)
    max_discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=100.00, help_text="Global limit for percentage discounts")
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=10000.00, help_text="Global limit for flat discounts")
    allow_percent_discount = models.BooleanField(default=True)
    allow_flat_discount = models.BooleanField(default=True)
    
    DISCOUNT_LEVEL_CHOICES = [
        ("ITEM_ONLY", "Item Level Only"),
        ("BILL_ONLY", "Bill Level Only"),
        ("BOTH", "Both Item & Bill Level"),
    ]
    allowed_discount_level = models.CharField(max_length=20, choices=DISCOUNT_LEVEL_CHOICES, default="BOTH", help_text="Global rule for where discounts can be applied")
    
    discount_tax_config = models.CharField(max_length=20, choices=[
        ("BEFORE_TAX", "Before Tax"),
        ("AFTER_TAX", "After Tax"),
    ], default="BEFORE_TAX", help_text="Global rule for discount application order")
    
    # 2. GLOBAL TAX CONFIGURATION
    gst_enabled = models.BooleanField(default=True)
    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    cgst_sgst_enabled = models.BooleanField(default=True, help_text="For intra-state")
    igst_enabled = models.BooleanField(default=True, help_text="For inter-state")
    tax_mode = models.CharField(max_length=20, choices=[
        ("INCLUSIVE", "Inclusive (Price includes tax)"),
        ("EXCLUSIVE", "Exclusive (Tax added to price)"),
    ], default="EXCLUSIVE")
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    
    # 3. INVOICE RULES & NUMBERING
    invoice_prefix = models.CharField(max_length=20, default="INV")
    invoice_starting_number = models.IntegerField(default=1001)
    auto_reset_frequency = models.CharField(max_length=20, choices=[
        ("MONTHLY", "Monthly"),
        ("YEARLY", "Yearly"),
        ("NEVER", "Never"),
    ], default="YEARLY")
    separate_pos_series = models.BooleanField(default=True)
    
    # 4. SUBSCRIPTION & ACCESS RULES
    default_trial_days = models.IntegerField(default=7)
    default_plan_after_trial = models.CharField(max_length=50, default="FREE")
    grace_period_days = models.IntegerField(default=3, help_text="Days after expiry before blocking")
    auto_block_on_expiry = models.BooleanField(default=True)
    
    # 5. REGISTRATION & ACCOUNT CONTROL
    allow_owner_signup = models.BooleanField(default=True)
    invite_only_mode = models.BooleanField(default=False)
    require_phone_otp = models.BooleanField(default=True)
    require_email_verification = models.BooleanField(default=True)
    
    # 6. SECURITY RULES
    password_min_length = models.IntegerField(default=8)
    password_require_uppercase = models.BooleanField(default=True)
    password_require_numbers = models.BooleanField(default=True)
    password_require_special_chars = models.BooleanField(default=True)
    session_timeout_minutes = models.IntegerField(default=30)
    max_login_attempts = models.IntegerField(default=5)
    enable_2fa = models.BooleanField(default=False)
    
    # 7. DATA & BACKUP RULES
    auto_backup_enabled = models.BooleanField(default=True)
    backup_frequency = models.CharField(max_length=20, choices=[
        ("DAILY", "Daily"),
        ("WEEKLY", "Weekly"),
        ("MONTHLY", "Monthly"),
    ], default="DAILY")
    data_retention_days = models.IntegerField(default=730, help_text="Days to retain data (0 = indefinite)")
    allow_data_export = models.BooleanField(default=True)
    
    # 8. PLATFORM BRANDING
    platform_name = models.CharField(max_length=255, default="Billing Application")
    company_name = models.CharField(max_length=255, default="Your Company")
    support_email = models.EmailField(default="support@example.com")
    support_phone = models.CharField(max_length=20, blank=True)
    primary_color = models.CharField(max_length=7, default="#3B82F6", help_text="Hex color code")
    default_theme = models.CharField(max_length=20, choices=[
        ("LIGHT", "Light"),
        ("DARK", "Dark"),
    ], default="DARK")
    
    # MISC
    currency = models.CharField(max_length=10, default="INR", choices=[
        ("INR", "Indian Rupee"),
        ("USD", "US Dollar"),
        ("EUR", "Euro"),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="settings_updates")

    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"

    def __str__(self):
        return f"System Settings (Updated: {self.updated_at})"

class ActivityLog(models.Model):
    """Audit trail for system activities"""
    ACTION_CHOICES = [
        ("CREATE_USER", "Created User"),
        ("SUSPEND_USER", "Suspended User"),
        ("ACTIVATE_USER", "Activated User"),
        ("DELETE_USER", "Deleted User"),
        ("UPDATE_SETTINGS", "Updated Settings"),
        ("UPDATE_GST", "Updated GST/Tax"),
        ("CREATE_CATEGORY", "Created Category"),
        ("UPDATE_CATEGORY", "Updated Category"),
        ("DELETE_CATEGORY", "Deleted Category"),
        ("CREATE_UNIT", "Created Unit"),
        ("UPDATE_UNIT", "Updated Unit"),
        ("DELETE_UNIT", "Deleted Unit"),
        ("LOGIN", "User Login"),
        ("LOGOUT", "User Logout"),
        ("OTHER", "Other Activity"),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="activity_logs")
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Activity Log"
        verbose_name_plural = "Activity Logs"

    def __str__(self):
        return f"{self.user} - {self.action} - {self.created_at}"

class Unit(models.Model):
    """Units for product measurement (kg, liter, piece, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    symbol = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.symbol})"
