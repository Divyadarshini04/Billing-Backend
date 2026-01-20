from django.core.management.base import BaseCommand
from apps.customer.models import Customer, CustomerAddress, LoyaltyTransaction

class Command(BaseCommand):
    help = 'Remove all dummy customer data from database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force delete all customers without confirmation',
        )

    def handle(self, *args, **options):
        count = Customer.objects.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No customers to delete.'))
            return
        
        if not options['force']:
            confirm = input(f'Are you sure you want to delete all {count} customers? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('Deletion cancelled.'))
                return
        
        # Delete all related data
        LoyaltyTransaction.objects.all().delete()
        CustomerAddress.objects.all().delete()
        Customer.objects.all().delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {count} customers and all related data.')
        )
