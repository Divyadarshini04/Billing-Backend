from rest_framework import serializers
from .models import Invoice, InvoiceItem, InvoiceReturn, DiscountRule, DiscountLog
from apps.super_admin.models import SystemSettings

class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = [
            'id', 'product', 'product_name', 'product_code', 'quantity',
            'unit_price', 'discount_percent', 'discount_amount', 'line_total',
            'tax_rate', 'tax_amount'
        ]

class CustomerBasicSerializer(serializers.Serializer):
    """Simplified customer serializer for nested use in invoices"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    phone = serializers.CharField()
    email = serializers.CharField(required=False, allow_blank=True)
    gstin = serializers.CharField(required=False, allow_blank=True)

class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    customer_gstin = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'owner', 'company_details', 'customer', 'customer_name', 'customer_phone', 'customer_email', 'customer_gstin', 'billing_mode',
            'subtotal', 'discount_amount', 'discount_percent',
            'cgst_amount', 'sgst_amount', 'igst_amount', 'tax_rate',
            'total_amount', 'paid_amount', 'payment_status', 'remaining_amount',
            'status', 'invoice_date', 'due_date', 'notes', 'items',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'invoice_number', 'owner', 'company_details', 'cgst_amount', 'sgst_amount', 'igst_amount',
            'total_amount', 'created_at', 'updated_at'
        ]

    def get_customer_name(self, obj):
        """Get customer name safely"""
        return obj.customer.name if obj.customer else None

    def get_customer_phone(self, obj):
        """Get customer phone safely"""
        return obj.customer.phone if obj.customer and obj.customer.phone else ""

    def get_customer_email(self, obj):
        """Get customer email safely"""
        return obj.customer.email if obj.customer and obj.customer.email else ""

    def get_customer_gstin(self, obj):
        """Get customer GSTIN safely"""
        return obj.customer.gstin if obj.customer and obj.customer.gstin else ""

    def get_remaining_amount(self, obj):
        return obj.get_remaining_amount()

class InvoiceReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceReturn
        fields = [
            'id', 'return_number', 'invoice', 'reason', 'returned_items',
            'return_amount', 'refund_amount', 'status', 'notes', 'created_at'
        ]
        read_only_fields = ['return_number', 'created_at']

class DiscountRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountRule
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Assign current user as creator
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

    def validate(self, data):
        """Enforce Super Admin Global Controls"""
        settings = SystemSettings.objects.first()
        if not settings:
            return data # Should ideally not happen, but fail safe

        # 1. Check if feature is enabled
        if not settings.enable_discounts:
            raise serializers.ValidationError({"detail": "Discount module is currently disabled by Super Admin."})

        discount_type = data.get('discount_type', self.instance.discount_type if self.instance else 'percentage')
        value = data.get('value', self.instance.value if self.instance else 0)

        # 2. Check Allowed Types
        if discount_type == 'percentage' and not settings.allow_percent_discount:
            raise serializers.ValidationError({"discount_type": "Percentage discounts are disabled by Super Admin."})
        
        if discount_type == 'flat' and not settings.allow_flat_discount:
             raise serializers.ValidationError({"discount_type": "Flat-rate discounts are disabled by Super Admin."})

        # 3. Check Global Limits
        if discount_type == 'percentage':
            if value > settings.max_discount_percentage:
                raise serializers.ValidationError({
                    "value": f"Percentage cannot exceed global limit of {settings.max_discount_percentage}% set by Super Admin."
                })
        
        elif discount_type == 'flat':
             if value > settings.max_discount_amount:
                raise serializers.ValidationError({
                    "value": f"Discount amount cannot exceed global limit of ₹{settings.max_discount_amount} set by Super Admin."
                })

        return data

class DiscountLogSerializer(serializers.ModelSerializer):
    rule_code = serializers.CharField(source='rule.code', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    user_name = serializers.CharField(source='applied_by.first_name', read_only=True)

    class Meta:
        model = DiscountLog
        fields = [
            'id', 'rule', 'rule_code', 'invoice', 'invoice_number', 
            'applied_by', 'user_name', 'discount_amount', 'timestamp'
        ]
        read_only_fields = ['timestamp']
