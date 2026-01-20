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

def remove_persistent_invoices():
    # List of invoice number patterns to search for
    target_patterns = [
        'IOPQNI-2025-90F95E',
        'IOPQNI-2025-38BE31',
        'INV-506721',
        'IIOP-2025-FD6101',
        'INP-2025-ECFB8E',
        'INYU-2025-7FDD3F'
    ]
    
    print(f"Searching for invoices matching: {target_patterns}")
    
    for pattern in target_patterns:
        # Search by exact match first
        invoices = Invoice.objects.filter(invoice_number__iexact=pattern)
        
        # If not found, try contains
        if not invoices.exists():
            invoices = Invoice.objects.filter(invoice_number__icontains=pattern)
            
        if invoices.exists():
            print(f"Found {invoices.count()} invoices matching '{pattern}':")
            for inv in invoices:
                print(f"  - Deleting Invoice: {inv.invoice_number} (ID: {inv.id})")
                
                # Delete linked returns
                returns = InvoiceReturn.objects.filter(invoice=inv)
                if returns.exists():
                    print(f"    - Deleting {returns.count()} linked returns...")
                    returns.delete()
                
                # Delete invoice
                inv.delete()
                print("    - Deleted.")
        else:
            print(f"No invoices found matching '{pattern}'.")

    # Double check visually
    print("\n--- Remaining Invoices (First 10) ---")
    for inv in Invoice.objects.all().order_by('-created_at')[:10]:
        print(f"{inv.invoice_number} | {inv.total_amount}")

if __name__ == '__main__':
    remove_persistent_invoices()
