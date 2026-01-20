from rest_framework import serializers
from .models import Customer, CustomerAddress, LoyaltyTransaction, LoyaltySettings

class LoyaltySettingsSerializer(serializers.ModelSerializer):
    """Serializer for global loyalty configuration."""
    class Meta:
        model = LoyaltySettings
        fields = ['points_per_rupee', 'redeem_value', 'bronze_threshold', 'silver_threshold', 'gold_threshold', 'platinum_threshold']

class CustomerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddress
        fields = ['id', 'type', 'address_line_1', 'address_line_2', 'city', 'state', 'postal_code', 'country', 'is_default']

class CustomerSerializer(serializers.ModelSerializer):
    addresses = CustomerAddressSerializer(many=True, read_only=True)
    available_credit = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id', 'phone', 'email', 'name', 'joined_date', 'gstin', 'uses_gst', 'customer_type',
            'status', 'loyalty_points', 'loyalty_tier', 'credit_limit',
            'current_credit_used', 'available_credit', 'notes', 'addresses',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'loyalty_points', 'loyalty_tier', 
            'current_credit_used', 'joined_date', 'available_credit'
        ]
        extra_kwargs = {
            'email': {'required': False, 'allow_blank': True, 'allow_null': True},
            'gstin': {'required': False, 'allow_blank': True, 'allow_null': True},
            'notes': {'required': False, 'allow_blank': True, 'allow_null': True},
            'phone': {'required': True},
            'name': {'required': True},
            'customer_type': {'required': False},
            'status': {'required': False}
        }

    def validate_phone(self, value):
        """Validate phone number format."""
        if not value:
            raise serializers.ValidationError("Phone is required")
        # Remove whitespace for validation
        phone_clean = value.strip()
        if len(phone_clean) < 7:
            raise serializers.ValidationError("Phone must be at least 7 characters long")
        if not any(c.isdigit() for c in phone_clean):
            raise serializers.ValidationError("Phone must contain at least one digit")
        return value
    
    def validate_name(self, value):
        """Validate name is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Name cannot be empty")
        return value
    
    def validate_email(self, value):
        """Allow blank/null emails."""
        if value is None or value == "":
            return None
        return value
    
    def validate_gstin(self, value):
        """Allow blank/null GSTIN."""
        if value is None or value == "":
            return None
        return value

    def validate(self, data):
        """Override validate to catch and provide better error messages."""
        try:
            # Log what we're validating

            return data
        except Exception as e:

            import traceback
            traceback.print_exc()
            raise

    def get_available_credit(self, obj):
        return obj.get_available_credit()

class LoyaltyTransactionSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    class Meta:
        model = LoyaltyTransaction
        fields = ['id', 'customer', 'customer_name', 'transaction_type', 'points', 'reference_id', 'description', 'created_at']
        read_only_fields = ['created_at']
