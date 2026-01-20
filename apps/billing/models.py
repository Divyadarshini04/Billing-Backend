from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.db.models import F, Sum, DecimalField, Index, UniqueConstraint, CheckConstraint, Q
from decimal import Decimal
from apps.customer.models import Customer
from apps.product.models import Product

class Invoice(models.Model):
    """POS Invoice/Bill information."""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    ]
    
    BILLING_MODE_CHOICES = [
        ('with_gst', 'With GST'),
        ('without_gst', 'Without GST'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
    ]

    invoice_number = models.CharField(max_length=50, db_index=True)
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices'
    )
    
    # Owner/Seller Details
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sales_invoices'
    )
    company_details = models.JSONField(default=dict, blank=True, help_text="Snapshot of company profile at time of invoice")
    
    # Billing details
    billing_mode = models.CharField(
        max_length=20,
        choices=BILLING_MODE_CHOICES,
        default='with_gst'
    )
    
    # Totals
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    # GST/Tax
    cgst_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    sgst_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    igst_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    # Final total
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    # Payment tracking
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='unpaid',
        db_index=True
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True
    )
    
    # Metadata
    invoice_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(blank=True, null=True)
    
    notes = models.TextField(blank=True, null=True)
    created_by_id = models.IntegerField(blank=True, null=True)  # User ID
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-invoice_date']
        indexes = [
            Index(fields=['invoice_number']),
            Index(fields=['customer', 'invoice_date']),
            Index(fields=['status', 'invoice_date']),
            Index(fields=['payment_status']),
        ]
        constraints = [
            UniqueConstraint(fields=['invoice_number', 'owner'], name='unique_invoice_number_per_owner'),
            CheckConstraint(check=Q(total_amount__gte=0), name='invoice_total_non_negative'),
            CheckConstraint(check=Q(paid_amount__lte=F('total_amount')), name='invoice_paid_lte_total'),
        ]

    def __str__(self):
        return f"Invoice-{self.invoice_number}"

    def calculate_tax(self):
        """Calculate and update GST amounts."""
        if self.billing_mode == 'without_gst':
            self.cgst_amount = Decimal('0')
            self.sgst_amount = Decimal('0')
            self.igst_amount = Decimal('0')
        else:
            # Default: CGST + SGST (18% total)
            # Convert tax_rate to Decimal to avoid type mismatch with float
            tax_rate_decimal = Decimal(str(self.tax_rate)) if not isinstance(self.tax_rate, Decimal) else self.tax_rate
            tax_amount = self.subtotal * (tax_rate_decimal / Decimal('100'))
            self.cgst_amount = tax_amount / 2
            self.sgst_amount = tax_amount / 2
            self.igst_amount = Decimal('0')

    def calculate_total(self):
        """Calculate invoice total."""
        self.calculate_tax()
        self.total_amount = self.subtotal - self.discount_amount + self.cgst_amount + self.sgst_amount + self.igst_amount
        return self.total_amount

    def get_remaining_amount(self):
        """Get unpaid amount."""
        return self.total_amount - self.paid_amount

    def cancel(self):
        """Cancel invoice."""
        self.status = 'cancelled'
        self.save()

    def complete(self):
        """Mark invoice as completed."""
        if self.status != 'cancelled':
            self.status = 'completed'
            self.save()

class InvoiceItem(models.Model):
    """Line items in an invoice."""
    
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='invoice_items')
    
    product_name = models.CharField(max_length=255)  # Store product name at time of sale
    product_code = models.CharField(max_length=50)
    
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"

    def calculate_line_total(self):
        """Calculate line item total with discount and tax."""
        subtotal = self.quantity * self.unit_price
        self.discount_amount = subtotal * (self.discount_percent / Decimal('100'))
        after_discount = subtotal - self.discount_amount
        
        if self.invoice.billing_mode == 'with_gst':
            self.tax_amount = after_discount * (self.tax_rate / Decimal('100'))
            self.line_total = after_discount + self.tax_amount
        else:
            self.tax_amount = Decimal('0')
            self.line_total = after_discount
        
        return self.line_total

class InvoiceReturn(models.Model):
    """Return/Refund against an invoice."""
    
    STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processed', 'Processed'),
    ]

    return_number = models.CharField(max_length=50, unique=True, db_index=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='returns')
    
    reason = models.CharField(max_length=255)
    returned_items = models.JSONField(default=list)  # List of {item_id, quantity}
    
    return_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    refund_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated', db_index=True)
    
    notes = models.TextField(blank=True, null=True)
    created_by_id = models.IntegerField(blank=True, null=True)
    processed_by_id = models.IntegerField(blank=True, null=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            Index(fields=['return_number']),
            Index(fields=['invoice', 'status']),
        ]

    def __str__(self):
        return f"Return-{self.return_number}"

class DiscountRule(models.Model):
    """Discount rules configured by the Owner."""
    
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('flat', 'Flat Amount'),
    ]
    
    APPLIES_TO_CHOICES = [
        ('item', 'Specific Item'),
        ('bill', 'Total Bill'),
    ]

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, help_text="Unique code for the discount (e.g., SUMMER10)")
    description = models.TextField(blank=True, null=True)
    
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    applies_to = models.CharField(max_length=20, choices=APPLIES_TO_CHOICES, default='bill')
    
    min_order_value = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Minimum bill amount required")
    max_discount_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, help_text="Maximum discount amount (for percentage type)")
    
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    
    is_active = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=False, help_text="If true, requires owner approval for sales executives")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_discounts')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='discounts',
        null=True,
        blank=True
    )

    def clean(self):
        from django.core.exceptions import ValidationError
        from apps.super_admin.models import SystemSettings
        from apps.common.models import CompanyProfile

        # 1. Check Global Settings (Super Admin)
        try:
            settings = SystemSettings.objects.first()
            if settings:
                if not settings.enable_discounts:
                    raise ValidationError("Discounts are globally disabled by Super Admin.")

                if self.discount_type == 'percentage':
                    if not settings.allow_percent_discount:
                        raise ValidationError("Percentage discounts are globally disabled.")
                    if self.value > settings.max_discount_percentage:
                        raise ValidationError(f"Discount cannot exceed global limit of {settings.max_discount_percentage}%.")
                
                if self.discount_type == 'flat':
                    if not settings.allow_flat_discount:
                        raise ValidationError("Flat amount discounts are globally disabled.")
                    if self.value > settings.max_discount_amount:
                        raise ValidationError(f"Discount amount cannot exceed global limit of {settings.max_discount_amount}.")
                
                # Check level restrictions
                if settings.allowed_discount_level == 'ITEM_ONLY' and self.applies_to == 'bill':
                    raise ValidationError("Global rules only allow Item-level discounts.")
                if settings.allowed_discount_level == 'BILL_ONLY' and self.applies_to == 'item':
                    raise ValidationError("Global rules only allow Bill-level discounts.")

        except SystemSettings.DoesNotExist:
            pass # Should ideally exist, but don't block if not init

        # 2. Check Company Settings (Owner) - Logic usually handled in Views/Serializers or here if we have context
        # Since DiscountRule is linked to created_by, we can infer company if needed, but usually CompanyProfile is global or 1:1 in this system
        # Assuming single tenant or handled by context.
        pass

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['code', 'owner'], name='unique_discount_code_per_owner'),
        ]
        ordering = ['-created_at']
        indexes = [
            Index(fields=['code']),
            Index(fields=['valid_from', 'valid_to']),
            Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.valid_from <= now <= self.valid_to

class DiscountLog(models.Model):
    """Audit log for applied discounts."""
    
    rule = models.ForeignKey(DiscountRule, on_delete=models.SET_NULL, null=True, related_name='usage_logs')
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='applied_discounts')
    applied_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='applied_discount_logs')
    
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.rule.code if self.rule else 'Unknown'} on {self.invoice.invoice_number}"
