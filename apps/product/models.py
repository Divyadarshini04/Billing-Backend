from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Index, UniqueConstraint, CheckConstraint, Q
from django.core.exceptions import ValidationError
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings

def validate_stock_non_negative(value):
    """Validator to ensure stock never goes negative."""
    if value < 0:
        raise ValidationError("Stock cannot be negative")

def validate_tax_rate(value):
    """Validator to ensure tax rate is between 0 and 100 (percentage)."""
    if value < 0 or value > 100:
        raise ValidationError("Tax rate must be between 0 and 100")

class Category(models.Model):
    """Category model with unique name and metadata."""
    name = models.CharField(max_length=100, db_index=True)
    description = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=7, default="#3B82F6", blank=True, null=True)  # Hex color code
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='categories',
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "Categories"
        indexes = [
            Index(fields=["name"]),
            Index(fields=["is_active", "created_at"]),
        ]
        constraints = [
            UniqueConstraint(fields=["name", "owner"], name="unique_category_name_per_owner"),
        ]

    def __str__(self):
        return self.name

class Product(models.Model):
    """Product model with validation, metadata, and constraints."""
    product_code = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    hsn_code = models.CharField(max_length=20, blank=True, null=True)
    unit = models.CharField(max_length=20, default="Piece", choices=[
        ('Piece', 'Piece'),
        ('Kg', 'Kg'),
        ('Litre', 'Litre'),
        ('Box', 'Box'),
        ('Meter', 'Meter')
    ])
    
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, validators=[validate_tax_rate])

    reorder_level = models.IntegerField(default=10, validators=[MinValueValidator(0)])
    reorder_quantity = models.IntegerField(default=10, validators=[MinValueValidator(1)])
    stock = models.IntegerField(default=0, validators=[validate_stock_non_negative])
    
    preferred_supplier = models.ForeignKey(
        'purchase.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='preferred_products'
    )

    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='products',
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["product_code"]),
            Index(fields=["name"]),
            Index(fields=["category", "is_active"]),
            Index(fields=["is_active", "created_at"]),
        ]
        constraints = [
            UniqueConstraint(fields=["product_code", "owner"], name="unique_product_code_per_owner"),
            CheckConstraint(check=Q(stock__gte=0), name="stock_non_negative"),
            CheckConstraint(check=Q(tax_rate__gte=0) & Q(tax_rate__lte=100), name="tax_rate_valid"),
        ]

    def __str__(self):
        return f"{self.name} ({self.product_code})"

    def is_low_stock(self):
        """Check if product is below reorder level."""
        return self.stock <= self.reorder_level

    def get_stock_value(self):
        """Get total inventory value (stock * unit_price)."""
        return self.stock * self.unit_price

    def deduct_stock(self, quantity, reference_id=None, reference_type='sale', user=None):
        """
        Deduct stock from product, prioritizing batches if they exist.
        """
        from .models import InventoryMovement  # Avoid circular dependency
        
        if quantity <= 0:
            return

        remaining_to_deduct = quantity
        
        # 1. Try batches first (FIFO by expiry and receipt)
        # Filter active batches with stock
        batches = self.batches.filter(remaining_quantity__gt=0).order_by('expiry_date', 'received_at')
        
        for batch in batches:
            if remaining_to_deduct <= 0:
                break
                
            deduct_amount = min(batch.remaining_quantity, remaining_to_deduct)
            
            batch.remaining_quantity -= deduct_amount
            batch.save()
            
            # Log movement for batch
            InventoryMovement.objects.create(
                batch=batch,
                product=self,
                change_type='sale',
                quantity=-deduct_amount,
                reference_id=reference_id,
                reference_type=reference_type,
                created_by_id=user.id if user else None
            )
            
            remaining_to_deduct -= deduct_amount
            
        # 2. Update total stock
        # We decrement the global stock counter regardless of batches
        # This assumes total stock is always the sum of batches + loose stock
        if self.stock >= quantity:
             self.stock -= quantity
        else:
             # Prevent negative stock if strict, or allow if business requirement?
             # For now, let's allow it to go 0 if it was positive, but the validator might block negative.
             # The validator validate_stock_non_negative will raise generic ValidationError if < 0
             self.stock -= quantity
             
        self.save()
        
        # 3. Log General Movement for any remainder (loose stock deduction)
        if remaining_to_deduct > 0:
             InventoryMovement.objects.create(
                batch=None,
                product=self,
                change_type='sale',
                quantity=-remaining_to_deduct, 
                reference_id=reference_id,
                reference_type=reference_type,
                created_by_id=user.id if user else None
            )

class InventoryBatch(models.Model):
    """Track inventory batches with supplier reference and expiry tracking."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="batches")
    batch_number = models.CharField(max_length=100, blank=True, null=True)
    
    supplier_id = models.IntegerField(blank=True, null=True)  # Will link to Supplier model later
    reference_purchase_id = models.IntegerField(blank=True, null=True)  # PurchaseOrder reference
    
    received_quantity = models.IntegerField(validators=[MinValueValidator(1)])
    remaining_quantity = models.IntegerField(validators=[MinValueValidator(0)])
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    manufacture_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    
    received_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-received_at"]
        indexes = [
            Index(fields=["product", "remaining_quantity"]),
            Index(fields=["expiry_date"]),
            Index(fields=["batch_number"]),
        ]
        constraints = [
            CheckConstraint(check=Q(remaining_quantity__lte=models.F('received_quantity')), name="remaining_lte_received"),
            CheckConstraint(check=Q(remaining_quantity__gte=0), name="remaining_non_negative"),
        ]

    def __str__(self):
        return f"Batch {self.batch_number} - {self.product.product_code}"

    def is_expired(self):
        """Check if batch is expired."""
        if not self.expiry_date:
            return False
        return timezone.now().date() > self.expiry_date

    def get_batch_value(self):
        """Get total batch value (remaining_quantity * unit_cost)."""
        return self.remaining_quantity * self.unit_cost

class InventoryMovement(models.Model):
    """Audit trail for all inventory movements (stock in/out)."""
    MOVEMENT_TYPES = [
        ('purchase', 'Purchase Receipt'),
        ('sale', 'Sale'),
        ('adjustment', 'Inventory Adjustment'),
        ('damage', 'Damage/Loss'),
        ('return', 'Customer Return'),
        ('transfer', 'Transfer'),
    ]

    batch = models.ForeignKey(InventoryBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name="movements")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="movements")
    
    change_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField()  # positive for in, negative for out
    
    reference_id = models.IntegerField(blank=True, null=True)  # Invoice ID, PurchaseOrder ID, etc.
    reference_type = models.CharField(max_length=50, blank=True)  # 'invoice', 'purchase', 'adjustment'
    
    notes = models.TextField(blank=True, null=True)
    created_by_id = models.IntegerField(blank=True, null=True)  # User ID
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["product", "created_at"]),
            Index(fields=["change_type", "created_at"]),
            Index(fields=["reference_id", "reference_type"]),
        ]

    def __str__(self):
        return f"{self.get_change_type_display()} - {self.product.product_code} ({self.quantity})"
