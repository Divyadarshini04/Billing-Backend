from django.core.management.base import BaseCommand
from apps.common.models import CompanyProfile
from apps.auth_app.models import User

class Command(BaseCommand):
    help = 'Fix the company profile ownership for Palani Aqua Connect'

    def handle(self, *args, **options):
        # Get user ID 40
        try:
            user = User.objects.get(id=40)
            self.stdout.write(f"User: {user.first_name} {user.last_name}")
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR("User ID 40 not found"))
            return

        # Find Palani Aqua Connect company
        try:
            palani_company = CompanyProfile.objects.get(company_name='Palani Aqua Connect')
            self.stdout.write(f"Found: {palani_company.company_name}")
        except CompanyProfile.DoesNotExist:
            self.stdout.write(self.style.ERROR("Palani Aqua Connect company not found"))
            return

        # Update the owner
        palani_company.owner = user
        palani_company.save()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Successfully linked {user.first_name} {user.last_name} to {palani_company.company_name}'
            )
        )
        
        # Verify
        updated_company = user.company_profile
        self.stdout.write(f"Verified: User's company is now {updated_company.company_name}")
