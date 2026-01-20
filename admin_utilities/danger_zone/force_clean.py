import os
# !!! WARNING: DESTRUCTIVE SCRIPT !!!
# This script modifies or deletes database records.
# Do not run unless you understand the consequences.
# Backup your database before execution.

import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.billing.models import Invoice, InvoiceReturn

def clean_all():
    invoices = Invoice.objects.all()
    count = invoices.count()
    print(f"Found {count} invoices.")
    
    for inv in invoices:
        try:
            print(f"Deleting {inv.invoice_number}...")
            # Manually delete related objects if cascading fails/protects
            # (Though on_delete should handle it, sometimes custom logic is needed)
            inv.delete()
            print("  - Done")
        except Exception as e:
            print(f"  - Error: {e}")

if __name__ == '__main__':
    clean_all()
