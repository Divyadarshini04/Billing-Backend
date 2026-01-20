from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import Index, CheckConstraint, Q
from django.utils import timezone

class InventoryAuditLog(models.Model):
    """Master audit log for all inventory operations."""
    OPERATION_TYPES = [
        ('batch_create', 'Batch Created'),
        ('batch_update', 'Batch Updated'),
        ('movement_record', 'Movement Recorded'),
        ('stock_adjust', 'Stock Adjusted'),
        ('batch_expire', 'Batch Expired'),
        ('physical_count', 'Physical Count'),
    ]

    operation_type = models.CharField(max_length=50, choices=OPERATION_TYPES, db_index=True)
    product_id = models.IntegerField()
    batch_id = models.IntegerField(blank=True, null=True)
    
    old_value = models.JSONField(blank=True, null=True)  # Previous state
    new_value = models.JSONField(blank=True, null=True)  # Current state
    
    user_id = models.IntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["product_id", "created_at"]),
            Index(fields=["batch_id", "created_at"]),
            Index(fields=["operation_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_operation_type_display()} - Product {self.product_id} at {self.created_at}"

class StockSyncLog(models.Model):
    """Track when product stock is synced from batches."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    products_count = models.IntegerField(default=0)
    updated_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    
    error_details = models.JSONField(blank=True, null=True)
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Stock Sync {self.status} - {self.started_at}"
