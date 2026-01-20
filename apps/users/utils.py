from apps.users.models import RolePermission, UserRole

def has_permission(user, code):
    """
    Check if user has a specific permission.
    Optimized to use .exists() instead of iterative checks.
    Superuser always returns True (bypass logic).
    """
    if not user or not user.is_authenticated:
        return False

    if getattr(user, "is_superuser", False):
        return True

    # Owner and Super Admin bypass: always has permission
    # This prevents issues where 'OWNER' role hasn't been assigned specific permissions in DB
    if UserRole.objects.filter(user=user, role__name__in=['OWNER', 'SUPER_ADMIN']).exists():
        return True

    # Use select_related/exists for optimized query
    return RolePermission.objects.filter(
        role__role_users__user=user,
        permission__code=code
    ).exists()
