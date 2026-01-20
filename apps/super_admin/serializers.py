from rest_framework import serializers
from apps.auth_app.models import User
from apps.subscription.models import UserSubscription
from apps.common.models import CompanyProfile
from apps.users.models import Role, UserRole
from .models import SystemSettings, ActivityLog, Unit

class SubscriptionInfoSerializer(serializers.ModelSerializer):
    """Serializer for subscription info"""
    plan_type = serializers.CharField(source="plan.code", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    expiry_date = serializers.DateTimeField(read_only=True, source="end_date")
    
    class Meta:
        model = UserSubscription
        fields = ["plan_type", "plan_name", "expiry_date", "status", "start_date", "end_date"]
        read_only_fields = ["status", "start_date", "end_date"]

class UserListSerializer(serializers.ModelSerializer):
    """Serializer for listing users in super admin panel"""
    role = serializers.SerializerMethodField()
    date_joined = serializers.DateTimeField(read_only=True)
    subscription = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "phone", "first_name", "last_name", "email", "business_type", "role", "is_active", "is_super_admin", "date_joined", "subscription"]
        read_only_fields = ["id", "date_joined"]

    def get_role(self, obj):
        """Get the primary role for the user"""
        if obj.is_super_admin:
            return "SUPER_ADMIN"
        return "OWNER"
    
    def get_subscription(self, obj):
        """Get subscription info for the user"""
        try:
            sub = UserSubscription.objects.get(user=obj, status='ACTIVE')
            return SubscriptionInfoSerializer(sub).data
        except UserSubscription.DoesNotExist:
            return None

class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed user serializer for super admin"""
    role = serializers.SerializerMethodField()
    date_joined = serializers.DateTimeField(read_only=True)
    last_login = serializers.DateTimeField(read_only=True)
    subscription = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "phone", "first_name", "last_name", "email", "business_type", "role", "is_active", "is_super_admin", "date_joined", "last_login", "subscription"]
        read_only_fields = ["id", "date_joined", "last_login"]

    def get_role(self, obj):
        """Get the primary role for the user"""
        if obj.is_super_admin:
            return "SUPER_ADMIN"
        return "OWNER"
    
    def get_subscription(self, obj):
        """Get subscription info for the user"""
        try:
            sub = UserSubscription.objects.get(user=obj, status='ACTIVE')
            return SubscriptionInfoSerializer(sub).data
        except UserSubscription.DoesNotExist:
            return None

class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users with optional company profile"""
    password = serializers.CharField(write_only=True, required=False)
    company_profile = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ["phone", "first_name", "last_name", "email", "business_type", "password", "company_profile"]

    def to_internal_value(self, data):
        """Clean data before validation"""
        if 'phone' in data:
            import re
            phone = data.get('phone')
            # Handle non-string types just in case
            if isinstance(phone, str):
                # Remove spaces, hyphens, plus signs
                clean_phone = re.sub(r'[\s\-+]', '', phone)
                # If it includes country code 91, strip it
                if len(clean_phone) > 10 and clean_phone.startswith('91'):
                    clean_phone = clean_phone[-10:]
                
                # Create mutable copy if needed
                if not isinstance(data, dict):
                    data = data.dict() # For QueryDict
                
                # Careful: modifying passed data if it's a dict reference validation relies on
                # Better to return new dict for super().to_internal_value if possible, 
                # but ModelSerializer expects dict-like data.
                data = data.copy()
                data['phone'] = clean_phone
                
        return super().to_internal_value(data)

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        company_profile_data = validated_data.pop('company_profile', None)
        
        user = User.objects.create_user(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        
        # Always create a company profile, even if not explicitly provided
        from django.utils import timezone
        import uuid

        if not company_profile_data:
            company_profile_data = {}

        # Default values using user data
        if 'company_name' not in company_profile_data:
            # Use last_name (Business Name) or fallback
            company_profile_data['company_name'] = user.last_name or f"Company-{user.phone}"
        
        if 'email' not in company_profile_data:
            company_profile_data['email'] = user.email or f"{user.phone}@example.com"
            
        if 'phone' not in company_profile_data:
            company_profile_data['phone'] = user.phone
            
        # Address defaults
        if 'street_address' not in company_profile_data:
            company_profile_data['street_address'] = "Not Provided"
        if 'city' not in company_profile_data:
            company_profile_data['city'] = "Not Provided"
        if 'state' not in company_profile_data:
            company_profile_data['state'] = "Not Provided"
        if 'postal_code' not in company_profile_data:
            company_profile_data['postal_code'] = "000000"
        if 'country' not in company_profile_data:
            company_profile_data['country'] = "India"

        # Unique fields generation if missing
        if 'company_code' not in company_profile_data:
            # First 3 chars of name + random
            base = company_profile_data['company_name'][:3].upper()
            suffix = uuid.uuid4().hex[:4].upper()
            company_profile_data['company_code'] = f"{base}-{suffix}"

        if 'tax_id' not in company_profile_data:
            # Placeholder tax ID
            company_profile_data['tax_id'] = f"NOT-REG-{uuid.uuid4().hex[:6].upper()}"
            
        if 'established_date' not in company_profile_data:
            company_profile_data['established_date'] = timezone.now().date()

        try:
            company_profile_data['owner'] = user
            CompanyProfile.objects.create(**company_profile_data)
        except Exception as e:
            # Log error but don't fail user creation
            print(f"Error creating company profile: {str(e)}")
        
        # Assign OWNER role
        try:
            owner_role = Role.objects.get(name="OWNER")
            UserRole.objects.create(user=user, role=owner_role)
        except Role.DoesNotExist:
            print("Error: OWNER role not found in database. User created without role.")
        except Exception as e:
            print(f"Error assigning OWNER role: {str(e)}")

        return user

    def to_representation(self, instance):
        return UserListSerializer(instance).data

class SystemSettingsSerializer(serializers.ModelSerializer):
    """Serializer for system settings - SUPER ADMIN ONLY"""
    class Meta:
        model = SystemSettings
        fields = [
            "id",
            # Feature Control
            "enable_pos_billing", "enable_inventory", "enable_gst_tax", "enable_loyalty_points",
            "enable_stock_alerts", "enable_invoice_pdf", "enable_sms_notifications", "enable_email_notifications",
            "enable_discounts",
            
            # Dashboard Feature Control
            "dashboard_access_enable",
            "dashboard_total_customers_card", "dashboard_total_products_card", "dashboard_total_revenue_card", "dashboard_active_customers_card",
            "dashboard_revenue_visibility",
            "dashboard_recent_orders_widget", "dashboard_invoice_number_visibility", "dashboard_order_amount_visibility", "dashboard_order_status_visibility",
            "dashboard_create_invoice_button", "dashboard_add_product_button", "dashboard_add_customer_button",
            "dashboard_notification_bell", "dashboard_data_calculation_enable",
            
            # Discount Rules
            "max_discount_percentage", "max_discount_amount", "allow_percent_discount", "allow_flat_discount",
            "allowed_discount_level", "discount_tax_config",
            
            # Tax Configuration
            "gst_enabled", "gst_percentage", "cgst_sgst_enabled", "igst_enabled", "tax_mode",
            # Invoice Rules
            "invoice_prefix", "invoice_starting_number", "auto_reset_frequency", "separate_pos_series",
            # Subscription Rules
            "default_trial_days", "default_plan_after_trial", "grace_period_days", "auto_block_on_expiry",
            # Registration Control
            "allow_owner_signup", "invite_only_mode", "require_phone_otp", "require_email_verification",
            # Security Rules
            "password_min_length", "password_require_uppercase", "password_require_numbers", 
            "password_require_special_chars", "session_timeout_minutes", "max_login_attempts", "enable_2fa",
            # Data & Backup
            "auto_backup_enabled", "backup_frequency", "data_retention_days", "allow_data_export",
            # Branding
            "platform_name", "company_name", "support_email", "support_phone", "primary_color", "default_theme",
            # Misc
            "currency", "updated_at"
        ]
        read_only_fields = ["id", "updated_at"]

class ActivityLogSerializer(serializers.ModelSerializer):
    """Serializer for activity logs"""
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    user_phone = serializers.CharField(source="user.phone", read_only=True)

    class Meta:
        model = ActivityLog
        fields = ["id", "user", "user_name", "user_phone", "action", "description", "ip_address", "created_at"]
        read_only_fields = ["id", "created_at"]

class UnitSerializer(serializers.ModelSerializer):
    """Serializer for units"""
    class Meta:
        model = Unit
        fields = ["id", "name", "symbol", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
