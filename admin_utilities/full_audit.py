import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.users.models import Role, UserRole
from apps.customer.models import Customer
from apps.product.models import Product, Category
from apps.billing.models import Invoice

User = get_user_model()

def audit():
    print("--- USER AUDIT ---")
    for u in User.objects.all():
        roles = [ur.role.name for ur in UserRole.objects.filter(user=u)]
        print(f"ID: {u.id} | Phone: {u.phone} | is_super: {u.is_super_admin} | Parent: {u.parent_id} | Roles: {roles} | Active: {u.is_active}")

    print("\n--- DATA ORPHAN AUDIT ---")
    c_orphans = Customer.objects.filter(owner__isnull=True).count()
    p_orphans = Product.objects.filter(owner__isnull=True).count()
    cat_orphans = Category.objects.filter(owner__isnull=True).count()
    i_orphans = Invoice.objects.filter(owner__isnull=True).count()
    
    print(f"Orphaned Customers: {c_orphans}")
    print(f"Orphaned Products: {p_orphans}")
    print(f"Orphaned Categories: {cat_orphans}")
    print(f"Orphaned Invoices: {i_orphans}")

    if c_orphans > 0:
        print("\n--- ORPHANED CUSTOMERS ---")
        for c in Customer.objects.filter(owner__isnull=True):
            print(f"  - {c.name} ({c.phone})")

if __name__ == "__main__":
    audit()
