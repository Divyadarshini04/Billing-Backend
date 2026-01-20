from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import Index
from decimal import Decimal
from apps.billing.models import Invoice

class PaymentMethod(models.Model):
    """Payment method types."""
    
    METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('upi', 'UPI'),
        ('netbanking', 'Net Banking'),
        ('wallet', 'Digital Wallet'),
        ('cheque', 'Cheque'),
        ('bank_transfer', 'Bank Transfer'),
    ]
    
    name = models.CharField(max_length=50, choices=METHOD_CHOICES, unique=True)
    is_active = models.BooleanField(default=True)
    requires_gateway = models.BooleanField(default=False)  # Razorpay, Stripe, etc.
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.get_name_display()

class Payment(models.Model):
    """Payment transaction record."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]

    payment_id = models.CharField(max_length=100, unique=True, db_index=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payments')
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True)
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    
    # Gateway information
    gateway_ref_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    gateway_response = models.JSONField(null=True, blank=True)
    
    # Metadata
    notes = models.TextField(blank=True, null=True)
    created_by_id = models.IntegerField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            Index(fields=['payment_id']),
            Index(fields=['invoice', 'status']),
            Index(fields=['gateway_ref_id']),
        ]

    def __str__(self):
        return f"Payment-{self.payment_id}"

class PaymentRefund(models.Model):
    """Refund transaction."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    refund_id = models.CharField(max_length=100, unique=True, db_index=True)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name='refunds')
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    reason = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    gateway_ref_id = models.CharField(max_length=255, blank=True, null=True)
    
    notes = models.TextField(blank=True, null=True)
    created_by_id = models.IntegerField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Refund-{self.refund_id}"
