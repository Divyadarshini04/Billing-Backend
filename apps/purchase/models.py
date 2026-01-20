from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import Index, UniqueConstraint, CheckConstraint, Q, F
from django.utils import timezone
from decimal import Decimal

class Supplier(models.Model):
    """Supplier/Vendor information."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('blocked', 'Blocked'),
    ]

    name = models.CharField(max_length=200, unique=True, db_index=True)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    contact_person = models.CharField(max_length=200, blank=True, null=True)
    
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    
    # Payment terms
    payment_terms = models.CharField(max_length=100, blank=True, null=True)  # e.g., "30 days", "COD"
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    
    # Tax information
    tax_id = models.CharField(max_length=50, blank=True, null=True)  # GST/VAT ID
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', db_index=True)
    
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            Index(fields=['code']),
            Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

class PurchaseOrder(models.Model):
    """Purchase Order header information."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('partially_received', 'Partially Received'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    ]

    po_number = models.CharField(max_length=50, unique=True, db_index=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, related_name='purchase_orders')
    
    order_date = models.DateTimeField(auto_now_add=True)
    expected_delivery_date = models.DateField(blank=True, null=True)
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', db_index=True)
    
    created_by_id = models.IntegerField(blank=True, null=True)  # User ID
    approved_by_id = models.IntegerField(blank=True, null=True)  # User ID
    approved_at = models.DateTimeField(blank=True, null=True)
    
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-order_date']
        indexes = [
            Index(fields=['po_number']),
            Index(fields=['supplier', 'order_date']),
            Index(fields=['status', 'order_date']),
            Index(fields=['payment_status', 'order_date']),
        ]
        constraints = [
            CheckConstraint(check=Q(total_amount__gte=0), name='total_non_negative'),
            CheckConstraint(check=Q(paid_amount__lte=F('total_amount')), name='paid_lte_total'),
        ]

    def __str__(self):
        return f"PO-{self.po_number}"

    def get_remaining_amount(self):
        """Calculate remaining payment."""
        return self.total_amount - self.paid_amount

    def get_completion_percentage(self):
        """Calculate order completion (by received quantity)."""
        if not hasattr(self, '_completion_percentage'):
            from apps.product.models import InventoryBatch
            total_ordered = self.items.aggregate(total=models.Sum('quantity'))['total'] or 0
            total_received = InventoryBatch.objects.filter(
                reference_purchase_id=self.id
            ).aggregate(total=models.Sum('received_quantity'))['total'] or 0
            
            if total_ordered == 0:
                self._completion_percentage = 0
            else:
                self._completion_percentage = (total_received / total_ordered) * 100
        return self._completion_percentage

    def is_overdue(self):
        """Check if order is overdue."""
        if not self.expected_delivery_date:
            return False
        return timezone.now().date() > self.expected_delivery_date and self.status not in ['received', 'cancelled']

class PurchaseOrderItem(models.Model):
    """Line items in a purchase order."""
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('product.Product', on_delete=models.SET_NULL, null=True, related_name='purchase_items')
    
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    
    received_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            Index(fields=['purchase_order', 'product']),
            Index(fields=['product', 'created_at']),
        ]
        constraints = [
            CheckConstraint(check=Q(received_quantity__lte=models.F('quantity')), name='received_lte_ordered'),
            CheckConstraint(check=Q(line_total__gte=0), name='line_total_non_negative'),
        ]

    def __str__(self):
        return f"PO Item - {self.product.name if self.product else 'N/A'}"

    def calculate_line_total(self):
        """Calculate line total: (quantity × unit_price) × (1 - discount%)."""
        subtotal = self.quantity * self.unit_price
        discount = subtotal * (self.discount_percent / Decimal('100'))
        return subtotal - discount

    def get_pending_quantity(self):
        """Get quantity still pending receipt."""
        return self.quantity - self.received_quantity

class PurchaseReceiptLog(models.Model):
    """GRN - Goods Receipt Note tracking."""
    grn_number = models.CharField(max_length=50, unique=True, db_index=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='receipts')
    
    receipt_date = models.DateTimeField(auto_now_add=True)
    received_by_id = models.IntegerField(blank=True, null=True)  # User ID
    
    # Delivery details
    invoice_number = models.CharField(max_length=50, blank=True, null=True)
    lr_number = models.CharField(max_length=50, blank=True, null=True)  # Logistics receipt
    carrier_name = models.CharField(max_length=200, blank=True, null=True)
    
    # Items received
    items_json = models.JSONField(default=dict)  # [{"item_id": X, "received_qty": Y, "batch_number": Z}]
    
    # Quality check
    quality_status = models.CharField(
        max_length=20,
        choices=[('accepted', 'Accepted'), ('partial', 'Partial'), ('rejected', 'Rejected')],
        default='accepted'
    )
    quality_notes = models.TextField(blank=True, null=True)
    
    # Cost details
    freight_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    other_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-receipt_date']
        indexes = [
            Index(fields=['grn_number']),
            Index(fields=['purchase_order', 'receipt_date']),
            Index(fields=['quality_status', 'receipt_date']),
        ]

    def __str__(self):
        return f"GRN-{self.grn_number}"

class PaymentRecord(models.Model):
    """Payment tracking for purchase orders."""
    PAYMENT_METHOD_CHOICES = [
        ('check', 'Check'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit', 'Credit'),
        ('cash', 'Cash'),
        ('upi', 'UPI'),
    ]

    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='payments')
    
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    
    reference_number = models.CharField(max_length=100, blank=True, null=True)  # Cheque/Transfer ID
    notes = models.TextField(blank=True, null=True)
    
    recorded_by_id = models.IntegerField(blank=True, null=True)  # User ID
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date']
        indexes = [
            Index(fields=['purchase_order', 'payment_date']),
            Index(fields=['payment_method', 'payment_date']),
        ]

    def __str__(self):
        return f"Payment {self.amount} for {self.purchase_order.po_number}"

class SupplierNotificationLog(models.Model):
    """
    Log of automatic/manual notifications sent to suppliers.
    """
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='notifications')
    product = models.ForeignKey('product.Product', on_delete=models.SET_NULL, null=True, related_name='supplier_notifications')
    
    notification_type = models.CharField(max_length=50, default='low_stock')
    
    sent_via = models.CharField(max_length=20, default='simulated') # email, sms, simulated
    status = models.CharField(max_length=20, default='success') # success, failed
    
    message_content = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            Index(fields=['supplier', 'created_at']),
        ]

    def __str__(self):
        return f"Notification to {self.supplier.name} re: {self.product.name if self.product else 'Unknown'}"
