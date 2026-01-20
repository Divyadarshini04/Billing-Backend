from rest_framework import serializers
from .models import Payment, PaymentRefund, PaymentMethod

class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['id', 'name', 'get_name_display', 'is_active', 'requires_gateway']

class PaymentSerializer(serializers.ModelSerializer):
    payment_method_name = serializers.CharField(source='payment_method.get_name_display', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    
    # Allow payment_method to be passed as name or ID
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def to_internal_value(self, data):
        # Handle payment_method as string name or integer ID
        if 'payment_method' in data:
            pm = data['payment_method']
            if isinstance(pm, str):
                # Try to find payment method by name
                try:
                    payment_method_obj = PaymentMethod.objects.get(name=pm)
                    data['payment_method'] = payment_method_obj.id
                except PaymentMethod.DoesNotExist:
                    # If not found, create it if it's a known method
                    if pm in dict(PaymentMethod.METHOD_CHOICES):
                        payment_method_obj, _ = PaymentMethod.objects.get_or_create(
                            name=pm,
                            defaults={'is_active': True}
                        )
                        data['payment_method'] = payment_method_obj.id
        return super().to_internal_value(data)

    class Meta:
        model = Payment
        fields = [
            'id', 'payment_id', 'invoice', 'invoice_number', 'amount',
            'payment_method', 'payment_method_name', 'status',
            'gateway_ref_id', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['payment_id', 'created_at', 'updated_at']

class PaymentRefundSerializer(serializers.ModelSerializer):
    payment_id = serializers.CharField(source='payment.payment_id', read_only=True)

    class Meta:
        model = PaymentRefund
        fields = [
            'id', 'refund_id', 'payment', 'payment_id', 'amount', 'reason',
            'status', 'gateway_ref_id', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['refund_id', 'created_at', 'updated_at']
