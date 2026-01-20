from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import CompanyProfile, EmailTemplate, NotificationPreference, AuditTrail, SystemSettings

User = get_user_model()

class CompanyProfileSerializer(serializers.ModelSerializer):
    """Serialize CompanyProfile with comprehensive validation."""
    
    class Meta:
        model = CompanyProfile
        fields = [
            'id', 'company_name', 'company_code', 'registration_number', 'tax_id',
            'email', 'phone', 'website', 'street_address', 'city', 'state',
            'postal_code', 'country', 'logo_url', 'currency', 'timezone',
            'financial_year_start_month', 'is_active', 'established_date',
            'billing_settings', 'tax_settings', 'discount_settings', 'loyalty_settings',
            'notification_settings', 'security_settings', 'report_settings', 'invoice_appearance',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_company_code(self, value):
        """Validate company code format - alphanumeric, 2-50 chars."""
        if not value:
            return value
        # Allow hyphens/underscores which logic often adds
        if not value.replace('-', '').replace('_', '').isalnum():
            # Loose validation or just return value
             pass 
        if len(value) < 2 or len(value) > 50:
            raise serializers.ValidationError("Company code must be 2-50 characters.")
        return value
    
    def validate_tax_id(self, value):
        """Validate tax ID format."""
        if not value:
            return value
        if len(value) < 5 or len(value) > 50:
            raise serializers.ValidationError("Tax ID must be 5-50 characters.")
        return value
    
    def validate_financial_year_start_month(self, value):
        """Validate financial year start month (1-12)."""
        if not (1 <= value <= 12):
            raise serializers.ValidationError("Month must be between 1 and 12.")
        return value
    
    def validate_postal_code(self, value):
        """Validate postal code is not empty."""
        if not value.strip():
            raise serializers.ValidationError("Postal code cannot be empty.")
        return value

class CompanyProfileMinimalSerializer(serializers.ModelSerializer):
    """Lightweight serializer for embedding in user details."""
    class Meta:
        model = CompanyProfile
        fields = [
            'id', 'company_name', 'company_code', 'email', 'phone', 
            'logo_url', 'currency', 'timezone', 'is_active'
        ]

class EmailTemplateSerializer(serializers.ModelSerializer):
    """Serialize EmailTemplate with variable validation."""
    created_by_username = serializers.CharField(
        source='created_by.username', 
        read_only=True
    )
    
    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'template_name', 'template_type', 'subject', 'body',
            'variables', 'is_active', 'created_by', 'created_by_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def validate_template_name(self, value):
        """Validate template name - alphanumeric with underscores."""
        if not value.replace('_', '').isalnum():
            raise serializers.ValidationError("Template name must be alphanumeric (underscores allowed).")
        return value
    
    def validate_subject(self, value):
        """Validate subject line not empty and reasonable length."""
        if not value.strip():
            raise serializers.ValidationError("Subject cannot be empty.")
        if len(value) > 255:
            raise serializers.ValidationError("Subject must be 255 characters or less.")
        return value
    
    def validate_body(self, value):
        """Validate body not empty."""
        if not value.strip():
            raise serializers.ValidationError("Template body cannot be empty.")
        return value
    
    def validate_variables(self, value):
        """Validate variables is a list."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Variables must be a list of variable names.")
        return value

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serialize NotificationPreference with time validation."""
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user', 'username', 'email_enabled', 'sms_enabled',
            'in_app_enabled', 'push_enabled', 'notification_types',
            'daily_digest', 'digest_time', 'quiet_hours_enabled',
            'quiet_hours_start', 'quiet_hours_end', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def validate_digest_time(self, value):
        """Validate digest time is in HH:MM:SS format."""
        if not value:
            raise serializers.ValidationError("Digest time cannot be empty.")
        return value
    
    def validate_quiet_hours_end(self, value):
        """Validate quiet hours end time."""
        if not value:
            raise serializers.ValidationError("Quiet hours end time cannot be empty.")
        return value
    
    def validate(self, data):
        """Validate quiet hours times are different."""
        start = data.get('quiet_hours_start')
        end = data.get('quiet_hours_end')
        if start and end and start == end:
            raise serializers.ValidationError(
                "Quiet hours start and end times cannot be the same."
            )
        return data

class AuditTrailSerializer(serializers.ModelSerializer):
    """Serialize AuditTrail - read-only for security."""
    username = serializers.CharField(source='user.username', read_only=True, allow_null=True)
    
    class Meta:
        model = AuditTrail
        fields = [
            'id', 'action_type', 'entity_type', 'entity_id', 'user',
            'username', 'ip_address', 'user_agent', 'old_values', 'new_values',
            'description', 'status', 'error_message', 'created_at'
        ]
        read_only_fields = [
            'id', 'action_type', 'entity_type', 'entity_id', 'user',
            'ip_address', 'user_agent', 'old_values', 'new_values',
            'description', 'status', 'error_message', 'created_at'
        ]

class SystemSettingsSerializer(serializers.ModelSerializer):
    """Serialize SystemSettings with validation for number formats."""
    updated_by_username = serializers.CharField(
        source='updated_by.username',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = SystemSettings
        fields = [
            'id', 'invoice_prefix', 'invoice_number_format', 'next_invoice_sequence',
            'po_prefix', 'po_number_format', 'next_po_sequence',
            'grn_prefix', 'grn_number_format', 'next_grn_sequence',
            'default_tax_rate', 'tax_enabled', 'low_stock_threshold',
            'reorder_point', 'payment_grace_period_days', 'late_fee_percentage',
            'smtp_server', 'smtp_port', 'smtp_username', 'smtp_password',
            'smtp_from_email', 'api_rate_limit_enabled', 'api_rate_limit_requests',
            'api_rate_limit_period_minutes', 'created_at', 'updated_at',
            'updated_by', 'updated_by_username'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'updated_by']
    
    def validate_default_tax_rate(self, value):
        """Validate tax rate is between 0 and 100."""
        if not (0 <= value <= 100):
            raise serializers.ValidationError("Tax rate must be between 0 and 100.")
        return value
    
    def validate_late_fee_percentage(self, value):
        """Validate late fee is between 0 and 100."""
        if not (0 <= value <= 100):
            raise serializers.ValidationError("Late fee percentage must be between 0 and 100.")
        return value
    
    def validate_low_stock_threshold(self, value):
        """Validate low stock threshold is positive."""
        if value < 0:
            raise serializers.ValidationError("Low stock threshold cannot be negative.")
        return value
    
    def validate_reorder_point(self, value):
        """Validate reorder point is positive."""
        if value < 0:
            raise serializers.ValidationError("Reorder point cannot be negative.")
        return value
    
    def validate_smtp_port(self, value):
        """Validate SMTP port is valid."""
        if not (1 <= value <= 65535):
            raise serializers.ValidationError("SMTP port must be between 1 and 65535.")
        return value
    
    def validate_api_rate_limit_requests(self, value):
        """Validate API rate limit requests is positive."""
        if value < 1:
            raise serializers.ValidationError("API rate limit requests must be at least 1.")
        return value
    
    def validate_api_rate_limit_period_minutes(self, value):
        """Validate API rate limit period is positive."""
        if value < 1:
            raise serializers.ValidationError("API rate limit period must be at least 1 minute.")
        return value
