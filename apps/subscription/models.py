from django.db import models
from django.utils import timezone
from apps.auth_app.models import User
from datetime import timedelta

class SubscriptionPlan(models.Model):
    """Subscription Plan definitions"""

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    duration_days = models.IntegerField(default=30)
    currency = models.CharField(max_length=10, default="INR")
    description = models.TextField(blank=True)
    features = models.JSONField(default=dict)
    max_staff_users = models.IntegerField(default=1, help_text="Maximum number of Sales Executives/staff users (0 = unlimited)")
    
    # Limits
    invoice_limit = models.CharField(max_length=50, default="100", help_text="e.g. '100', '1000', 'Unlimited'")
    product_limit = models.CharField(max_length=50, default="Unlimited", help_text="e.g. '20', '200', 'Unlimited'")
    customer_limit = models.CharField(max_length=50, default="Unlimited", help_text="e.g. '20', 'Unlimited'")
    business_limit = models.CharField(max_length=50, default="1", help_text="e.g. '1', 'Multiple'")
    branch_limit = models.CharField(max_length=50, default="1", help_text="e.g. '1', 'Unlimited'")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

class UserSubscription(models.Model):
    """Active subscription for a user"""
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("EXPIRED", "Expired"),
        ("CANCELLED", "Cancelled"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    auto_renew = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    payment_details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.first_name} - {self.plan.name}"

    def is_active(self):
        return self.status == "ACTIVE" and self.end_date > timezone.now()

    def save(self, *args, **kwargs):
        if not self.end_date and self.plan:
            self.end_date = self.start_date + timedelta(days=self.plan.duration_days)
        super().save(*args, **kwargs)
