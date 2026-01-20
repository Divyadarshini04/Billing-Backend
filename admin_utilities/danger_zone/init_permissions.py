
import os
# !!! WARNING: DESTRUCTIVE SCRIPT !!!
# This script modifies or deletes database records.
# Do not run unless you understand the consequences.
# Backup your database before execution.

import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.users.models import Role, Permission, RolePermission, UserRole
from apps.auth_app.models import User

# --- Constants matching Frontend ---
ROLES = ['OWNER', 'SALES_EXECUTIVE']

PERMISSIONS = {
    'OWNER': [
        'view_dashboard', 'manage_dashboard',
        'view_customers', 'manage_customers', 'export_customers', 'import_customers',
        'view_inventory', 'manage_inventory', 'export_inventory', 'import_inventory',
        'view_reports', 'manage_reports', 'export_reports',
        'view_pos', 'manage_pos', 'export_pos',
        'view_invoices', 'manage_invoices', 'export_invoices',
        'view_subscription', 'manage_subscription',
        'manage_users', 'assign_roles',
        'manage_settings', 'view_audit_logs',
        'export_all', 'import_all',
        'view_loyalty', 'manage_loyalty'
    ],
    'SALES_EXECUTIVE': [
        'view_dashboard',
        'view_customers', 'manage_customers', 'export_customers',
        'view_inventory', 'export_inventory',
        'view_reports', 'export_reports',
        'view_pos', 'manage_pos', 'export_pos',
        'view_invoices', 'manage_invoices', 'export_invoices',
        'view_loyalty', 'manage_loyalty'
    ]
}

def init_roles_and_permissions():
    print("Initializing Roles and Permissions...")

    # 1. Create Roles
    for role_name in ROLES:
        role, created = Role.objects.get_or_create(name=role_name)
        if created:
            print(f"Created Role: {role_name}")
        else:
            print(f"Role exists: {role_name}")

    # 2. Create Permissions (Using the union of all permission codes)
    all_perms = set()
    for role_rules in PERMISSIONS.values():
        all_perms.update(role_rules)
    
    for perm_code in all_perms:
        perm, created = Permission.objects.get_or_create(code=perm_code)
        if created:
            print(f"Created Permission: {perm_code}")

    # 3. Assign Default Permissions to Roles
    for role_name, perm_codes in PERMISSIONS.items():
        role = Role.objects.get(name=role_name)
        for perm_code in perm_codes:
            perm = Permission.objects.get(code=perm_code)
            rp, created = RolePermission.objects.get_or_create(role=role, permission=perm)
            if created:
                print(f"Assigned {perm_code} to {role_name}")
    
    # 4. Assign OWNER Role to existing users who are NOT super admin and have no role
    # This is a fallback to ensure the current logged-in user has a role
    users = User.objects.filter(is_super_admin=False)
    owner_role = Role.objects.get(name='OWNER')
    
    for user in users:
        # Check if user has any role
        if not UserRole.objects.filter(user=user).exists():
            UserRole.objects.create(user=user, role=owner_role)
            print(f"Assigned OWNER role to user {user.phone}")

    print("Initialization Complete.")

if __name__ == '__main__':
    init_roles_and_permissions()
