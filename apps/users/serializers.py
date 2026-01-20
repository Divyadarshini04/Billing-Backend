from rest_framework import serializers
from .models import User, Role, Permission, RolePermission
from apps.users.models import UserRole

class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role with metadata."""
    class Meta:
        model = Role
        fields = ["id", "name", "description", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at", "id"]
    
    def validate_name(self, value):
        """Validate role name is not empty."""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Role name cannot be empty")
        return value

class PermissionSerializer(serializers.ModelSerializer):
    """Serializer for Permission with metadata."""
    class Meta:
        model = Permission
        fields = ["id", "code", "description", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at", "id"]
    
    def validate_code(self, value):
        """Validate permission code is not empty."""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Permission code cannot be empty")
        return value

class RolePermissionSerializer(serializers.ModelSerializer):
    """Serializer for RolePermission assignment with duplicate validation."""
    role_name = serializers.CharField(source="role.name", read_only=True)
    permission_code = serializers.CharField(source="permission.code", read_only=True)
    
    class Meta:
        model = RolePermission
        fields = ["id", "role", "role_name", "permission", "permission_code", "created_at"]
        read_only_fields = ["created_at", "id"]
    
    def validate(self, data):
        """Check for duplicate assignment before save."""
        role = data.get('role')
        permission = data.get('permission')
        
        if role and permission:
            if RolePermission.objects.filter(role=role, permission=permission).exists():
                raise serializers.ValidationError(
                    {"detail": "This permission is already assigned to this role"}
                )
        
        return data

class UserRoleSerializer(serializers.ModelSerializer):
    """Serializer for UserRole assignment with duplicate validation."""
    phone = serializers.CharField(source="user.phone", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    
    class Meta:
        model = UserRole
        fields = ["id", "user", "phone", "role", "role_name", "created_at"]
        read_only_fields = ["created_at", "id"]
    
    def validate(self, data):
        """Check for duplicate assignment before save."""
        user = data.get('user')
        role = data.get('role')
        
        if user and role:
            if UserRole.objects.filter(user=user, role=role).exists():
                raise serializers.ValidationError(
                    {"detail": "This role is already assigned to this user"}
                )
        
        return data

class UserDetailedRoleSerializer(serializers.ModelSerializer):
    """Serializer for user roles with structured format: [{id, name}]."""
    id = serializers.IntegerField(source="role.id")
    name = serializers.CharField(source="role.name")
    
    class Meta:
        model = UserRole
        fields = ["id", "name"]

class UserSerializer(serializers.ModelSerializer):
    """Serializer for User with structured roles and optimized queries."""
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "phone", "first_name", "last_name", "email", "is_active", "roles"]
        read_only_fields = ["id"]

    def get_roles(self, obj):
        """Return structured roles format: [{id, name}]."""
        # Use prefetch_related in the queryset to optimize queries
        if hasattr(obj, '_prefetched_objects_cache'):
            # If prefetch_related was used, the data is already cached
            user_roles = obj.user_roles.all()
        else:
            # Fallback with select_related for individual objects
            user_roles = obj.user_roles.select_related("role").all()
        
        return [
            {
                "id": ur.role.id,
                "name": ur.role.name
            } for ur in user_roles
        ]

class StaffCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating staff members.
    Handles password hashing and default role assignment.
    """
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "password"]
    
    def to_internal_value(self, data):
        """Clean data before validation."""
        # Make mutable copy if needed (DRF data can be immutable)
        if hasattr(data, 'copy'):
            data = data.copy()
            
        if 'phone' in data and data['phone']:
            # Clean phone number to just 10 digits
            digits = ''.join(filter(str.isdigit, str(data['phone'])))
            # Take last 10 digits
            if len(digits) > 10:
                digits = digits[-10:]
            data['phone'] = digits
            
        return super().to_internal_value(data)
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        # User model has username=None, so we do NOT pass username
             
        user = User.objects.create_user(password=password, **validated_data)
        return user
