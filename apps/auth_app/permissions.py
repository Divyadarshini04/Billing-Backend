from rest_framework.permissions import BasePermission
from apps.users.utils import has_permission

class IsAdminOrSuperUser(BasePermission):
    """Check if user is superuser or has admin role."""

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        # Check via UserRole relationship
        from apps.users.models import UserRole, Role
        return UserRole.objects.filter(
            user=user,
            role__name="admin"
        ).exists()

class IsAdminOrHasPermission(BasePermission):
    """
    Check if user is superuser, admin, or has specific permission.
    View should define required_permission attribute.
    
    Usage in view:
        class SomeAdminView(APIView):
            permission_classes = [IsAdminOrHasPermission]
            required_permission = "can_manage_roles"  # optional
    """

    def has_permission(self, request, view):
        user = request.user

        # Must be authenticated
        if not user or not user.is_authenticated:
            return False

        # Superuser bypass
        if getattr(user, "is_superuser", False):
            return True

        # Check required permission on view
        required_permission = getattr(view, "required_permission", None)
        
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"PERMISSION CHECK: User={user.id} ({user.phone}), Required={required_permission}")
        if not required_permission:
            # No specific permission required, check admin role
            from apps.users.models import UserRole
            val = UserRole.objects.filter(
                user=user,
                role__name="admin"
            ).exists()
            logger.warning(f"PERMISSION CHECK: No required permission. Is Admin? {val}")
            return val

        # Check if user has the required permission via role
        from apps.users.models import UserRole, RolePermission
        from apps.users.models import Permission
        
        try:
            permission_obj = Permission.objects.get(code=required_permission)
        except Permission.DoesNotExist:
            logger.warning(f"PERMISSION CHECK: Permission '{required_permission}' does not exist in DB!")
            return False

        # Check if user's role has this permission
        has_perm = RolePermission.objects.filter(
            role__role_users__user=user,
            permission=permission_obj
        ).exists()
        
        logger.warning(f"PERMISSION CHECK: User {user.id} has permission '{required_permission}'? {has_perm}")
        
        # DEBUG: Print user roles
        roles = UserRole.objects.filter(user=user).values_list('role__name', flat=True)
        logger.warning(f"PERMISSION CHECK: User Roles: {list(roles)}")

        return has_perm

class IsAdmin(BasePermission):
    """
    Permission class to allow only admin/superuser.
    """
    
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_superuser)

class IsAuthenticated(BasePermission):
    """
    Permission class to allow only authenticated users.
    """
    
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated)

class IsSuperAdmin(BasePermission):
    """
    Allows access to users who are super admins (flag) or have the SUPERADMIN role.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
            
        # Allow Django superuser, system super admin flag, or role string
        return (
            bool(getattr(user, 'is_superuser', False)) or
            bool(getattr(user, 'is_super_admin', False)) or 
            getattr(user, 'role', '') == 'SUPERADMIN'
        )
