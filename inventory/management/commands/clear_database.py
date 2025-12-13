from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

class Command(BaseCommand):
    help = 'Clears all data from the database safely (without TRUNCATE).'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('⚠️  Clearing all data from the database...'))

        with transaction.atomic():
            # Loop over all models
            for model in apps.get_models():
                try:
                    model.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS(f"Deleted all rows from {model._meta.label}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to delete {model._meta.label}: {e}"))

        self.stdout.write(self.style.SUCCESS('✅ All data cleared successfully!'))
