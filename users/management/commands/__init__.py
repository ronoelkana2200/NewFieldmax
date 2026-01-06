from django.core.management.base import BaseCommand
from users.models import Role

class Command(BaseCommand):
    help = 'Creates default roles if they do not exist'

    def handle(self, *args, **kwargs):
        roles = [
            'Admin',
            'Manager',
            'Sales Representative',
            'Field Agent',
            'Supervisor',
            'Cashier',
            'Agent'
        ]

        created_count = 0
        for role_name in roles:
            role, created = Role.objects.get_or_create(name=role_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Created role: {role_name}'))
                created_count += 1
            else:
                self.stdout.write(f'- Role already exists: {role_name}')

        self.stdout.write(self.style.SUCCESS(f'\nTotal roles in database: {Role.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Created {created_count} new roles'))