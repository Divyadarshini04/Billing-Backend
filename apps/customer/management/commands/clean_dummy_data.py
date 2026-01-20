from django.core.management.base import BaseCommand
from apps.customer.models import Customer
from apps.product.models import Product
from apps.billing.models import Invoice, InvoiceItem
from apps.payment.models import Payment

class Command(BaseCommand):
    help = 'Delete all dummy/test data and start fresh'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Delete all customers, products, invoices, and payments',
        )

    def handle(self, *args, **options):
        if options['all']:
            # Delete all data
            customers_count = Customer.objects.count()
            products_count = Product.objects.count()
            invoices_count = Invoice.objects.count()
            payments_count = Payment.objects.count()
            
            Customer.objects.all().delete()
            Product.objects.all().delete()
            Invoice.objects.all().delete()
            InvoiceItem.objects.all().delete()
            Payment.objects.all().delete()
            
            self.stdout.write(self.style.SUCCESS(
                f'Successfully deleted:\n'
                f'  - {customers_count} customers\n'
                f'  - {products_count} products\n'
                f'  - {invoices_count} invoices\n'
                f'  - {payments_count} payments\n'
                f'\nDatabase is now clean!'
            ))
        else:
            # Show current counts
            customers_count = Customer.objects.count()
            products_count = Product.objects.count()
            invoices_count = Invoice.objects.count()
            payments_count = Payment.objects.count()
            
            self.stdout.write(self.style.WARNING(
                f'Current data counts:\n'
                f'  - {customers_count} customers\n'
                f'  - {products_count} products\n'
                f'  - {invoices_count} invoices\n'
                f'  - {payments_count} payments\n\n'
                f'Run with --all flag to delete all dummy data:\n'
                f'  python manage.py clean_dummy_data --all'
            ))
