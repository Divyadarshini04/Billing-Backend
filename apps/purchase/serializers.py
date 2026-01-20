from rest_framework import serializers
from apps.purchase.models import Supplier, PurchaseOrder, PurchaseOrderItem, PurchaseReceiptLog, PaymentRecord
from apps.product.models import Product
from decimal import Decimal

class SupplierSerializer(serializers.ModelSerializer):
    """Serializer for supplier information."""
    
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'code', 'email', 'phone', 'contact_person',
            'address', 'city', 'state', 'postal_code', 'country',
            'payment_terms', 'credit_limit', 'tax_id', 'status', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_code(self, value):
        """Validate supplier code is unique."""
        if self.instance and self.instance.code == value:
            return value
        if Supplier.objects.filter(code=value).exists():
            raise serializers.ValidationError("Supplier code must be unique.")
        return value

    def validate_credit_limit(self, value):
        """Validate credit limit is non-negative."""
        if value < 0:
            raise serializers.ValidationError("Credit limit cannot be negative.")
        return value

    def validate(self, data):
        """Validate phone format if provided."""
        phone = data.get('phone')
        if phone and not phone.isdigit() and len(phone) < 7:
            raise serializers.ValidationError({'phone': 'Invalid phone number.'})
        return data

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    """Serializer for purchase order items."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    pending_quantity = serializers.IntegerField(source='get_pending_quantity', read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'purchase_order', 'product', 'product_name', 'product_code',
            'quantity', 'unit_price', 'discount_percent', 'line_total',
            'received_quantity', 'pending_quantity', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'line_total', 'created_at', 'updated_at']

    def validate_product(self, value):
        """Validate product exists and is active."""
        if not Product.objects.filter(id=value.id, is_active=True).exists():
            raise serializers.ValidationError("Product not found or inactive.")
        return value

    def validate_quantity(self, value):
        """Validate quantity is positive."""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0.")
        return value

    def validate_unit_price(self, value):
        """Validate unit price is non-negative."""
        if value < 0:
            raise serializers.ValidationError("Unit price cannot be negative.")
        return value

    def validate_discount_percent(self, value):
        """Validate discount is 0-100."""
        if value < 0 or value > 100:
            raise serializers.ValidationError("Discount must be between 0 and 100.")
        return value

    def validate_received_quantity(self, value):
        """Validate received quantity is non-negative."""
        if value < 0:
            raise serializers.ValidationError("Received quantity cannot be negative.")
        return value

    def validate(self, data):
        """Validate received_qty doesn't exceed ordered qty."""
        received = data.get('received_quantity', self.instance.received_quantity if self.instance else 0)
        quantity = data.get('quantity', self.instance.quantity if self.instance else 0)
        
        if received > quantity:
            raise serializers.ValidationError(
                "Received quantity cannot exceed ordered quantity."
            )
        return data

    def create(self, validated_data):
        """Calculate line_total on creation."""
        validated_data['line_total'] = PurchaseOrderItem(**validated_data).calculate_line_total()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Recalculate line_total on update."""
        instance = super().update(instance, validated_data)
        instance.line_total = instance.calculate_line_total()
        instance.save()
        return instance

class PurchaseOrderSerializer(serializers.ModelSerializer):
    """Serializer for purchase orders."""
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    remaining_amount = serializers.DecimalField(
        source='get_remaining_amount',
        read_only=True,
        max_digits=12,
        decimal_places=2
    )
    completion_percentage = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'supplier', 'supplier_name', 'order_date',
            'expected_delivery_date', 'subtotal', 'tax_amount', 'shipping_cost',
            'total_amount', 'paid_amount', 'remaining_amount', 'status',
            'payment_status', 'created_by_id', 'approved_by_id', 'approved_at',
            'notes', 'items', 'completion_percentage', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'po_number', 'order_date', 'supplier_name', 'items',
            'remaining_amount', 'completion_percentage', 'created_at', 'updated_at'
        ]

    def validate_supplier(self, value):
        """Validate supplier is active."""
        if value.status != 'active':
            raise serializers.ValidationError("Supplier is not active.")
        return value

    def validate_total_amount(self, value):
        """Validate total amount is non-negative."""
        if value < 0:
            raise serializers.ValidationError("Total amount cannot be negative.")
        return value

    def validate_paid_amount(self, value):
        """Validate paid amount is non-negative."""
        if value < 0:
            raise serializers.ValidationError("Paid amount cannot be negative.")
        return value

    def validate(self, data):
        """Validate paid_amount doesn't exceed total_amount."""
        paid = data.get('paid_amount')
        total = data.get('total_amount', self.instance.total_amount if self.instance else 0)
        
        if paid and paid > total:
            raise serializers.ValidationError(
                "Paid amount cannot exceed total amount."
            )
        return data

    def get_completion_percentage(self, obj):
        """Get order completion percentage."""
        return round(obj.get_completion_percentage(), 2)

class PurchaseReceiptLogSerializer(serializers.ModelSerializer):
    """Serializer for purchase receipt logs (GRN)."""
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)

    class Meta:
        model = PurchaseReceiptLog
        fields = [
            'id', 'grn_number', 'purchase_order', 'po_number', 'receipt_date',
            'received_by_id', 'invoice_number', 'lr_number', 'carrier_name',
            'items_json', 'quality_status', 'quality_notes', 'freight_charge',
            'other_charges', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'grn_number', 'receipt_date', 'po_number', 'created_at', 'updated_at'
        ]

    def validate_quality_status(self, value):
        """Validate quality status."""
        valid_choices = ['accepted', 'partial', 'rejected']
        if value not in valid_choices:
            raise serializers.ValidationError(f"Quality status must be one of {valid_choices}.")
        return value

    def validate_freight_charge(self, value):
        """Validate freight charge is non-negative."""
        if value < 0:
            raise serializers.ValidationError("Freight charge cannot be negative.")
        return value

    def validate_other_charges(self, value):
        """Validate other charges is non-negative."""
        if value < 0:
            raise serializers.ValidationError("Other charges cannot be negative.")
        return value

    def validate_items_json(self, value):
        """Validate items JSON structure."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Items must be a JSON object.")
        
        # Expected format: {"item_id": X, "received_qty": Y, "batch_number": Z}
        required_fields = ['item_id', 'received_qty', 'batch_number']
        if value and not all(field in value for field in required_fields):
            raise serializers.ValidationError(f"Items must contain fields: {required_fields}.")
        
        return value

class PaymentRecordSerializer(serializers.ModelSerializer):
    """Serializer for payment records."""
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)

    class Meta:
        model = PaymentRecord
        fields = [
            'id', 'purchase_order', 'po_number', 'payment_date', 'amount',
            'payment_method', 'payment_method_display', 'reference_number',
            'notes', 'recorded_by_id', 'created_at'
        ]
        read_only_fields = ['id', 'po_number', 'payment_method_display', 'created_at']

    def validate_amount(self, value):
        """Validate payment amount is positive."""
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than 0.")
        return value

    def validate_payment_date(self, value):
        """Validate payment date is not in the future."""
        from django.utils import timezone
        if value > timezone.now().date():
            raise serializers.ValidationError("Payment date cannot be in the future.")
        return value

    def validate(self, data):
        """Validate payment doesn't exceed PO total."""
        purchase_order = data.get('purchase_order')
        amount = data.get('amount')
        
        if purchase_order and amount:
            total_paid = purchase_order.paid_amount + amount
            if total_paid > purchase_order.total_amount:
                raise serializers.ValidationError(
                    f"Payment amount exceeds remaining balance. "
                    f"Remaining: {purchase_order.get_remaining_amount()}"
                )
        return data

class PurchaseOrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for PO list view."""
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'supplier', 'supplier_name', 'order_date',
            'total_amount', 'paid_amount', 'status', 'payment_status',
            'item_count'
        ]

    def get_item_count(self, obj):
        """Get number of items in PO."""
        return obj.items.count()
