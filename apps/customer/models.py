from django.db import models
from django.core.validators import MinValueValidator, RegexValidator, EmailValidator
from django.db.models import Index, UniqueConstraint, Q
from django.utils import timezone
from django.conf import settings
from decimal import Decimal

def get_today():
    """Return today's date."""
    return timezone.now().date()

class LoyaltySettings(models.Model):
    """
    Global configuration for the Loyalty Program.
    Singleton model - only one active instance should exist.
    """
    points_per_rupee = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=1.00,
        help_text="How many points earned per 1 Rupee spent"
    )
    redeem_value = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.10,
        help_text="Value of 1 point in Rupees (e.g. 0.10 means 10 points = ₹1)"
    )
    
    # Tier Thresholds
    bronze_threshold = models.IntegerField(default=0)
    silver_threshold = models.IntegerField(default=1000)
    gold_threshold = models.IntegerField(default=3000)
    platinum_threshold = models.IntegerField(default=5000)
    
    # Metadata
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Loyalty Settings"
        verbose_name_plural = "Loyalty Settings"

    def __str__(self):
        return "Loyalty Configuration"

    def save(self, *args, **kwargs):
        """Ensure singleton pattern."""
        if not self.pk and LoyaltySettings.objects.exists():
            # If trying to create a new one but one exists, update the existing one
            return
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Get or create the settings."""
        settings, created = cls.objects.get_or_create(id=1)
        return settings

class Customer(models.Model):
    """Customer information with loyalty and GST support."""
    
    CUSTOMER_TYPE_CHOICES = [
        ('retail', 'Retail'),
        ('wholesale', 'Wholesale'),
        ('corporate', 'Corporate'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]

    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^[0-9+\-\s()]{7,20}$', 'Phone must contain at least 7 digits')]
    )
    email = models.EmailField(blank=True, null=True, validators=[EmailValidator()])
    name = models.CharField(max_length=200)
    joined_date = models.DateField(default=get_today)
    
    # GST Information
    gstin = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$', 'Invalid GSTIN format')]
    )
    uses_gst = models.BooleanField(default=True, help_text="Whether GST applies to this customer's invoices")
    
    customer_type = models.CharField(
        max_length=20,
        choices=CUSTOMER_TYPE_CHOICES,
        default='retail'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        db_index=True
    )
    
    # Loyalty Program
    loyalty_points = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    loyalty_tier = models.CharField(
        max_length=20,
        choices=[
            ('bronze', 'Bronze'),
            ('silver', 'Silver'),
            ('gold', 'Gold'),
            ('platinum', 'Platinum'),
        ],
        default='bronze'
    )
    
    # Credit Limit
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    current_credit_used = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='customers',
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            Index(fields=['phone']),
            Index(fields=['email']),
            Index(fields=['status']),
            Index(fields=['customer_type']),
            Index(fields=['created_at']),
        ]
        constraints = [
            UniqueConstraint(fields=['phone', 'owner'], name='unique_customer_phone_per_owner'),
            UniqueConstraint(fields=['gstin', 'owner'], name='unique_customer_gstin_per_owner', condition=Q(gstin__isnull=False)),
        ]

    def __str__(self):
        return f"{self.name} ({self.phone})"

    def get_available_credit(self):
        """Calculate available credit."""
        return self.credit_limit - self.current_credit_used

    def get_pending_amount(self):
        """Calculate total pending amount from unpaid/partial invoices."""
        from apps.billing.models import Invoice
        from django.db.models import F, Sum
        
        # Get all unpaid and partial invoices
        pending_invoices = Invoice.objects.filter(
            customer=self,
            payment_status__in=['unpaid', 'partial']
        ).aggregate(
            total_pending=Sum(F('total_amount') - F('paid_amount'), output_field=models.DecimalField())
        )
        
        return pending_invoices['total_pending'] or Decimal('0')

    def add_loyalty_points(self, points):
        """Add loyalty points and update tier."""
        self.loyalty_points += points
        self._update_loyalty_tier()
        self.save()

    def _update_loyalty_tier(self):
        """Update tier based on loyalty points."""
        # Get thresholds from settings
        # Note: Ideally this should fetch from LoyaltySettings, but for performance in model method
        # we might want to pass it in or rely on cached values. 
        # For now, keeping hardcoded default logic fallback if needed, or query.
        try:
            settings = LoyaltySettings.objects.first()
            if settings:
                if self.loyalty_points >= settings.platinum_threshold:
                    self.loyalty_tier = 'platinum'
                elif self.loyalty_points >= settings.gold_threshold:
                    self.loyalty_tier = 'gold'
                elif self.loyalty_points >= settings.silver_threshold:
                    self.loyalty_tier = 'silver'
                else:
                    self.loyalty_tier = 'bronze'
                return
        except:
            pass
            
        # Fallback defaults
        if self.loyalty_points >= 5000:
            self.loyalty_tier = 'platinum'
        elif self.loyalty_points >= 3000:
            self.loyalty_tier = 'gold'
        elif self.loyalty_points >= 1000:
            self.loyalty_tier = 'silver'
        else:
            self.loyalty_tier = 'bronze'

class CustomerAddress(models.Model):
    """Multiple addresses for a customer."""
    
    ADDRESS_TYPE_CHOICES = [
        ('billing', 'Billing'),
        ('shipping', 'Shipping'),
        ('other', 'Other'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='addresses')
    
    type = models.CharField(
        max_length=20,
        choices=ADDRESS_TYPE_CHOICES,
        default='shipping'
    )
    
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='India')
    
    is_default = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']
        unique_together = ['customer', 'type', 'is_default']

    def __str__(self):
        return f"{self.customer.name} - {self.type}"

    def save(self, *args, **kwargs):
        """Ensure only one default address per type."""
        if self.is_default:
            CustomerAddress.objects.filter(
                customer=self.customer,
                type=self.type,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

class LoyaltyTransaction(models.Model):
    """Track loyalty points transactions."""
    
    TRANSACTION_TYPE_CHOICES = [
        ('earn', 'Earn'),
        ('redeem', 'Redeem'),
        ('adjust', 'Adjustment'),
        ('expire', 'Expired'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loyalty_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    points = models.IntegerField(validators=[MinValueValidator(1)])
    
    reference_id = models.CharField(max_length=100, blank=True, null=True)  # Invoice ID, etc.
    description = models.CharField(max_length=255)
    
    created_by_id = models.IntegerField(blank=True, null=True)  # User ID
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            Index(fields=['customer', 'created_at']),
            Index(fields=['transaction_type']),
        ]

    def __str__(self):
        return f"{self.customer.name} - {self.transaction_type} - {self.points}"
