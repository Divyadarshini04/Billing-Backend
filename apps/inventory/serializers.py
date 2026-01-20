from rest_framework import serializers
from apps.product.models import Product, InventoryBatch, InventoryMovement
from apps.inventory.models import InventoryAuditLog, StockSyncLog

class InventoryBatchSerializer(serializers.ModelSerializer):
    """Serializer for inventory batches with validation and nested product info."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    is_expired = serializers.SerializerMethodField()
    batch_value = serializers.DecimalField(
        source='get_batch_value',
        read_only=True,
        max_digits=12,
        decimal_places=2
    )

    class Meta:
        model = InventoryBatch
        fields = [
            'id', 'product_id', 'product_name', 'product_code', 'batch_number',
            'supplier_id', 'reference_purchase_id',
            'received_quantity', 'remaining_quantity', 'unit_cost',
            'manufacture_date', 'expiry_date', 'is_expired', 'batch_value',
            'received_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'is_expired', 'batch_value', 'received_at', 'created_at', 'updated_at'
        ]

    def validate_product_id(self, value):
        """Validate product exists."""
        if not Product.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Product not found or inactive.")
        return value

    def validate_remaining_quantity(self, value):
        """Validate remaining quantity is non-negative."""
        if value < 0:
            raise serializers.ValidationError("Remaining quantity cannot be negative.")
        return value

    def validate_received_quantity(self, value):
        """Validate received quantity is positive."""
        if value <= 0:
            raise serializers.ValidationError("Received quantity must be positive.")
        return value

    def validate_unit_cost(self, value):
        """Validate unit cost is non-negative."""
        if value < 0:
            raise serializers.ValidationError("Unit cost cannot be negative.")
        return value

    def validate(self, data):
        """Validate remaining quantity does not exceed received quantity."""
        received_qty = data.get('received_quantity')
        remaining_qty = data.get('remaining_quantity', received_qty)
        
        if remaining_qty > received_qty:
            raise serializers.ValidationError(
                "Remaining quantity cannot exceed received quantity."
            )
        return data

    def get_is_expired(self, obj):
        """Check if batch is expired."""
        return obj.is_expired()

    def create(self, validated_data):
        """Create batch with product relationship."""
        product_id = validated_data.pop('product_id')
        product = Product.objects.get(id=product_id)
        return InventoryBatch.objects.create(product=product, **validated_data)

class InventoryMovementSerializer(serializers.ModelSerializer):
    """Serializer for inventory movements with audit trail."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    movement_display = serializers.CharField(
        source='get_change_type_display',
        read_only=True
    )

    class Meta:
        model = InventoryMovement
        fields = [
            'id', 'product', 'product_name', 'batch', 'batch_number',
            'change_type', 'movement_display', 'quantity',
            'reference_id', 'reference_type', 'notes',
            'created_by_id', 'created_at'
        ]
        read_only_fields = [
            'id', 'product_name', 'batch_number', 'movement_display', 'created_at'
        ]

    def validate_quantity(self, value):
        """Validate quantity is non-zero."""
        if value == 0:
            raise serializers.ValidationError("Quantity cannot be zero.")
        return value

    def validate(self, data):
        """Validate product and batch relationship if batch provided."""
        batch = data.get('batch')
        product = data.get('product')
        
        if batch and batch.product != product:
            raise serializers.ValidationError(
                "Batch must belong to the specified product."
            )
        return data

class InventoryAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit logs with operation details."""
    operation_display = serializers.CharField(
        source='get_operation_type_display',
        read_only=True
    )

    class Meta:
        model = InventoryAuditLog
        fields = [
            'id', 'operation_type', 'operation_display', 'product_id',
            'batch_id', 'old_value', 'new_value', 'user_id', 'notes', 'created_at'
        ]
        read_only_fields = [
            'id', 'operation_display', 'created_at'
        ]

class StockSyncLogSerializer(serializers.ModelSerializer):
    """Serializer for stock synchronization logs."""
    
    class Meta:
        model = StockSyncLog
        fields = [
            'id', 'status', 'products_count', 'updated_count', 'error_count',
            'error_details', 'started_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'status', 'started_at', 'completed_at'
        ]

class BatchListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for batch list endpoints."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.product_code', read_only=True)

    class Meta:
        model = InventoryBatch
        fields = [
            'id', 'product_id', 'product_name', 'product_code', 'batch_number',
            'received_quantity', 'remaining_quantity', 'unit_cost',
            'expiry_date', 'received_at'
        ]
