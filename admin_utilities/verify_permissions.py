
import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.users.models import Role, Permission, RolePermission, UserRole
from apps.auth_app.models import User
from apps.users.utils import has_permission

def check_user_perms():
    with open("verify_result.txt", "w", encoding="utf-8") as f:
        f.write("Checking permissions for non-superuser users...\n")
        
        users = User.objects.filter(is_super_admin=False)
        
        if not users.exists():
            f.write("No standard users found.\n")
            return

        for user in users:
            f.write(f"\nUser: {user.phone} (ID: {user.id})\n")
            f.write(f"Is SuperUser: {user.is_superuser}\n")
            
            user_roles = UserRole.objects.filter(user=user)
            if not user_roles.exists():
                f.write("  [!] No roles assigned to this user.\n")
                continue
                
            for ur in user_roles:
                f.write(f"  Role: {ur.role.name} (assigned at {ur.created_at})\n")
                
                perm_code = 'manage_settings'
                has_perm_db = RolePermission.objects.filter(role=ur.role, permission__code=perm_code).exists()
                f.write(f"    - Role has '{perm_code}': {has_perm_db}\n")
                
            has_perm_util = has_permission(user, 'manage_settings')
            f.write(f"  has_permission(user, 'manage_settings') -> {has_perm_util}\n")

            perms = RolePermission.objects.filter(role__role_users__user=user).values_list('permission__code', flat=True)
            f.write(f"  All Permissions: {list(perms)}\n")

if __name__ == '__main__':
    check_user_perms()
