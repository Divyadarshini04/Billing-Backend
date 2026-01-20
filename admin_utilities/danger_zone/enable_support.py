import os
import sys
import django

# ==========================================
# ⚠️ DANGER ZONE: REPAIR SCRIPT ⚠️
# This script modifies database records.
# Run only if you understand the consequences.
# ==========================================

# Add the project root to the path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.users.models import Role, Permission, RolePermission

def enable_support():
    try:
        owner_role = Role.objects.get(name='OWNER')
        print(f"Found Owner Role: {owner_role}")

        # Check if permission exists
        try:
            support_perm = Permission.objects.get(code='view_support')
            print(f"Found Permission: {support_perm}")
        except Permission.DoesNotExist:
            print("Permission 'view_support' not found. Creating it.")
            support_perm = Permission.objects.create(
                code='view_support',
                description='Permission to view support tickets'
            )
            
        # Assign permission
        rp, created = RolePermission.objects.get_or_create(role=owner_role, permission=support_perm)
        if created:
            print("Successfully assigned 'view_support' to OWNER.")
        else:
            print("'view_support' is already assigned to OWNER.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    enable_support()
