import re
from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.users.models import Role

# More flexible phone validation - allows any 10-digit number for development
PHONE_REGEX = r'^[0-9]{10}$'

User = get_user_model()

class SendOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)

    def validate_phone(self, value):
        if not value or not re.match(PHONE_REGEX, value):
            raise serializers.ValidationError("Please enter a valid 10-digit phone number")
        return value

class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6, min_length=6)

    def validate_phone(self, value):
        if not value or not re.match(PHONE_REGEX, value):
            raise serializers.ValidationError("Invalid Indian phone number")
        return value
    
    def validate_code(self, value):
        if not value:
            raise serializers.ValidationError("OTP code is required")
        return value

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name"]

class UserMinimalSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    parent_name = serializers.SerializerMethodField()
    company_profile = serializers.SerializerMethodField()
    max_staff_allowed = serializers.IntegerField(source='get_max_staff_allowed', read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "phone", "roles", "role", "is_super_admin", "first_name", 
            "last_name", "email", "is_active", "parent", "parent_name", 
            "company_profile", "max_staff_allowed"
        ]

    def get_parent_name(self, obj):
        if obj.parent:
            return f"{obj.parent.first_name} {obj.parent.last_name} ({obj.parent.phone})"
        return "N/A"

    def get_roles(self, obj):
        """Return structured role format with id and name."""
        roles = Role.objects.filter(role_users__user=obj)
        return [{"id": r.id, "name": r.name} for r in roles]

    def get_role(self, obj):
        """Return first role name as 'role' field for backward compatibility."""
        if obj.is_super_admin:
            return "SUPERADMIN"
        roles = Role.objects.filter(role_users__user=obj)
        if roles.exists():
            return roles.first().name
        return "USER"  # Default role if none assigned

    def get_company_profile(self, obj):
        """Get company profile for the user (or their owner)."""
        owner = obj.parent if obj.parent else obj
        try:
            from django.apps import apps
            CompanyProfile = apps.get_model('common', 'CompanyProfile')
            
            profile = CompanyProfile.objects.filter(owner=owner).first()
            if not profile:
                 profile = CompanyProfile.objects.filter(is_active=True).first()
            
            if profile:
                return {
                    'id': profile.id,
                    'company_name': profile.company_name,
                    'company_code': profile.company_code,
                    'tax_id': profile.tax_id,
                    'email': profile.email,
                    'phone': profile.phone,
                    'street_address': profile.street_address,
                    'city': profile.city,
                    'state': profile.state,
                    'postal_code': profile.postal_code,
                    'logo_url': profile.logo_url,
                    'currency': profile.currency,
                    'timezone': profile.timezone,
                    'is_active': profile.is_active
                }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching company profile: {e}")
        return None
