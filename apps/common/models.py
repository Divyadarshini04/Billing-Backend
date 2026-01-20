from django.db import models
from django.conf import settings
from django.core.validators import URLValidator, EmailValidator
from django.utils import timezone
import json

# CompanyProfile - Store company/organization information
class CompanyProfile(models.Model):
    """
    Company/organization profile for the billing system.
    Linked to an Owner user for multi-tenancy.
    """
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='company_profile', null=True, blank=True)
    company_name = models.CharField(max_length=255, unique=True)
    company_code = models.CharField(max_length=50, unique=True)
    registration_number = models.CharField(max_length=100, blank=True, null=True)
    tax_id = models.CharField(max_length=50, unique=True)
    email = models.EmailField(validators=[EmailValidator()])
    phone = models.CharField(max_length=20)
    website = models.URLField(blank=True, null=True, validators=[URLValidator()])
    
    # Address
    street_address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    
    # Logo and branding
    logo_url = models.TextField(blank=True, null=True)
    
    # Company settings
    currency = models.CharField(max_length=3, default='USD')  # ISO 4217
    timezone = models.CharField(max_length=63, default='UTC')
    financial_year_start_month = models.IntegerField(default=1)  # 1-12
    
    # Status
    is_active = models.BooleanField(default=True)
    established_date = models.DateField()
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Detailed Settings Groups
    billing_settings = models.JSONField(default=dict, blank=True, help_text="Prefix, numbering, due days, payment modes")
    tax_settings = models.JSONField(default=dict, blank=True, help_text="GST enabled, rates, types")
    discount_settings = models.JSONField(default=dict, blank=True, help_text="Enable discounts, limits, approval")
    loyalty_settings = models.JSONField(default=dict, blank=True, help_text="Points logic, expiry, redemption")
    notification_settings = models.JSONField(default=dict, blank=True, help_text="Alert toggles")
    security_settings = models.JSONField(default=dict, blank=True, help_text="2FA, timeouts")
    report_settings = models.JSONField(default=dict, blank=True, help_text="Access control for reports")
    invoice_appearance = models.JSONField(default=dict, blank=True, help_text="Theme, footer, terms")

    class Meta:
        verbose_name = 'Company Profile'
        verbose_name_plural = 'Company Profiles'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company_code']),
            models.Index(fields=['tax_id']),
            models.Index(fields=['is_active']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(financial_year_start_month__gte=1, 
                              financial_year_start_month__lte=12),
                name='valid_fy_start_month'
            ),
        ]
    
    def __str__(self):
        return f"{self.company_name} ({self.company_code})"

# EmailTemplate - Store email templates for notifications
class EmailTemplate(models.Model):
    """
    Reusable email templates for system notifications.
    Supports variable substitution: {{order_number}}, {{customer_name}}, {{amount}}, etc.
    """
    TEMPLATE_TYPES = [
        ('order_confirmation', 'Order Confirmation'),
        ('order_shipped', 'Order Shipped'),
        ('payment_received', 'Payment Received'),
        ('payment_overdue', 'Payment Overdue'),
        ('inventory_low', 'Low Inventory Alert'),
        ('purchase_approved', 'Purchase Order Approved'),
        ('receipt_created', 'Goods Receipt Created'),
        ('user_welcome', 'User Welcome'),
        ('password_reset', 'Password Reset'),
        ('custom', 'Custom Template'),
    ]
    
    template_name = models.CharField(max_length=100, unique=True)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES)
    subject = models.CharField(max_length=255)  # Can include variables: {{company_name}}
    body = models.TextField()  # HTML body with variables
    
    # Template variables documentation
    variables = models.JSONField(
        default=list, 
        help_text='List of supported variables: {{order_number}}, {{customer_name}}, {{amount}}, {{date}}, etc.'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='email_templates_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Email Template'
        verbose_name_plural = 'Email Templates'
        ordering = ['template_type', 'template_name']
        indexes = [
            models.Index(fields=['template_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.template_name} ({self.get_template_type_display()})"

# NotificationPreference - User notification settings
class NotificationPreference(models.Model):
    """
    User notification preferences - control which notifications they receive and how.
    """
    NOTIFICATION_CHANNELS = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('in_app', 'In-App'),
        ('push', 'Push Notification'),
    ]
    
    NOTIFICATION_TYPES = [
        ('order_created', 'Order Created'),
        ('order_updated', 'Order Updated'),
        ('order_shipped', 'Order Shipped'),
        ('payment_received', 'Payment Received'),
        ('payment_overdue', 'Payment Overdue'),
        ('inventory_low', 'Low Inventory'),
        ('purchase_approved', 'Purchase Approved'),
        ('purchase_received', 'Purchase Received'),
        ('system_alert', 'System Alert'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preference')
    
    # Channels enabled
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    in_app_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    
    # Notification type preferences (JSON for flexibility)
    notification_types = models.JSONField(
        default=dict,
        help_text='Dict mapping notification types to enabled status'
    )
    
    # Frequency settings
    daily_digest = models.BooleanField(default=False)
    digest_time = models.TimeField(default='09:00:00')  # HH:MM:SS
    
    # Quiet hours (no notifications between these times)
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(default='22:00:00')
    quiet_hours_end = models.TimeField(default='07:00:00')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notifications for {self.user.username}"

# AuditTrail - Track all system changes
class AuditTrail(models.Model):
    """
    Comprehensive audit logging for compliance and debugging.
    Tracks all CRUD operations across all modules.
    """
    ACTION_TYPES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('retrieve', 'Retrieve'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('permission_change', 'Permission Change'),
        ('config_change', 'Configuration Change'),
    ]
    
    # What happened
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    entity_type = models.CharField(max_length=100)  # Model name: 'Product', 'PurchaseOrder', etc.
    entity_id = models.CharField(max_length=100)  # ID of affected record
    
    # Who did it
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='audit_actions')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Changes made (old → new)
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    
    # Additional context
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='success')  # success, error, pending
    error_message = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Audit Trail'
        verbose_name_plural = 'Audit Trails'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action_type', 'created_at']),
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_action_type_display()} {self.entity_type} by {self.user or 'System'}"

# SystemSettings - Global application settings
class SystemSettings(models.Model):
    """
    Global system configuration that can be updated without code changes.
    Singleton pattern - only one instance should exist.
    """
    # Invoice settings
    invoice_prefix = models.CharField(max_length=20, default='INV')
    invoice_number_format = models.CharField(
        max_length=50, 
        default='{PREFIX}-{YEAR}{MONTH}-{SEQUENCE}',
        help_text='Format: {PREFIX}, {YEAR}, {MONTH}, {SEQUENCE}, {DAY}'
    )
    next_invoice_sequence = models.IntegerField(default=1000)
    
    # PurchaseOrder settings
    po_prefix = models.CharField(max_length=20, default='PO')
    po_number_format = models.CharField(
        max_length=50,
        default='{PREFIX}-{YEAR}-{SEQUENCE}',
        help_text='Format: {PREFIX}, {YEAR}, {SEQUENCE}'
    )
    next_po_sequence = models.IntegerField(default=100)
    
    # GRN (Goods Receipt Note) settings
    grn_prefix = models.CharField(max_length=20, default='GRN')
    grn_number_format = models.CharField(
        max_length=50,
        default='{PREFIX}-{YEAR}-{SEQUENCE}',
        help_text='Format: {PREFIX}, {YEAR}, {SEQUENCE}'
    )
    next_grn_sequence = models.IntegerField(default=500)
    
    # Tax settings
    default_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    tax_enabled = models.BooleanField(default=True)
    
    # Inventory settings
    low_stock_threshold = models.IntegerField(default=50)
    reorder_point = models.IntegerField(default=100)
    
    # Payment settings
    payment_grace_period_days = models.IntegerField(default=0)
    late_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=2.00)
    
    # Email settings
    smtp_server = models.CharField(max_length=255, blank=True)
    smtp_port = models.IntegerField(default=587)
    smtp_username = models.CharField(max_length=255, blank=True)
    smtp_password = models.CharField(max_length=255, blank=True)
    smtp_from_email = models.EmailField(blank=True)
    
    # API settings
    api_rate_limit_enabled = models.BooleanField(default=True)
    api_rate_limit_requests = models.IntegerField(default=100)
    api_rate_limit_period_minutes = models.IntegerField(default=60)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='system_settings_updates')
    
    class Meta:
        verbose_name = 'System Settings'
        verbose_name_plural = 'System Settings'
    
    def __str__(self):
        return "System Settings"
    
    def save(self, *args, **kwargs):
        """Ensure only one SystemSettings instance exists."""
        if not self.pk and SystemSettings.objects.exists():
            existing = SystemSettings.objects.first()
            self.pk = existing.pk
        super().save(*args, **kwargs)

# AppNotification - In-app notifications for users (e.g., Owner)
class AppNotification(models.Model):
    """
    In-app alerts for users (e.g., Low Stock, High Demand).
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='app_notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    related_link = models.CharField(max_length=255, blank=True, null=True)  # e.g., '/inventory?status=Low%20Stock'
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
        ]
        
    def __str__(self):
        return f"{self.title} - {self.user.username}"
