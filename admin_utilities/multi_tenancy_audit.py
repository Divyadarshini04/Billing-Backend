import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.customer.models import Customer
from apps.users.models import Role, UserRole

User = get_user_model()

print("--- MULTI-TENANCY AUDIT ---")
users = User.objects.filter(parent__isnull=True)
for u in users:
    roles = [ur.role.name for ur in UserRole.objects.filter(user=u)]
    if u.is_super_admin:
        roles.append("SUPERADMIN")
    
    customers = Customer.objects.filter(owner=u)
    print(f"Owner: {u.phone} | is_super: {u.is_super_admin} | Roles: {roles} | Customers Count: {customers.count()}")
    for c in customers:
        print(f"  - Customer: {c.name} ({c.phone})")

print("\n--- CUSTOMERS WITH NO OWNER ---")
orphans = Customer.objects.filter(owner__isnull=True)
print(f"Orphaned Customers: {orphans.count()}")
for o in orphans:
    print(f"  - Orphan: {o.name} ({o.phone})")
