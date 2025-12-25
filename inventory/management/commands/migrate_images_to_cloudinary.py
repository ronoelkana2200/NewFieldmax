"""
Management command to migrate existing local images to Cloudinary

Usage:
python manage.py migrate_images_to_cloudinary
"""

from django.core.management.base import BaseCommand
from inventory.models import Product
import cloudinary.uploader
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Migrate existing local product images to Cloudinary'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually doing it',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('MIGRATING IMAGES TO CLOUDINARY'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made\n'))

        # Get all products with images
        products_with_images = Product.objects.exclude(image='').exclude(image__isnull=True)
        total_products = products_with_images.count()

        self.stdout.write(f"Found {total_products} products with images\n")

        success_count = 0
        error_count = 0
        skipped_count = 0

        for index, product in enumerate(products_with_images, 1):
            self.stdout.write(f"\n[{index}/{total_products}] Processing: {product.name} ({product.product_code})")
            
            try:
                # Check if already on Cloudinary
                image_url = str(product.image.url)
                if 'cloudinary.com' in image_url or 'res.cloudinary.com' in image_url:
                    self.stdout.write(self.style.WARNING(f"  ⏭️  Already on Cloudinary: {image_url}"))
                    skipped_count += 1
                    continue

                # Get local file path
                try:
                    local_path = product.image.path
                except Exception:
                    # Path might not have extension, try to find the file
                    base_path = os.path.join(settings.MEDIA_ROOT, product.image.name)
                    
                    # Try common extensions
                    possible_paths = [
                        base_path + '.jpg',
                        base_path + '.jpeg',
                        base_path + '.png',
                        base_path + '.webp',
                        base_path + '.gif',
                    ]
                    
                    local_path = None
                    for possible_path in possible_paths:
                        if os.path.exists(possible_path):
                            local_path = possible_path
                            break
                    
                    if not local_path:
                        self.stdout.write(self.style.ERROR(f"  ❌ Could not find file for: {product.image.name}"))
                        error_count += 1
                        continue
                
                if not os.path.exists(local_path):
                    # Try to find file with extension
                    base_path = os.path.join(settings.MEDIA_ROOT, product.image.name)
                    possible_paths = [
                        base_path + '.jpg',
                        base_path + '.jpeg', 
                        base_path + '.png',
                        base_path + '.webp',
                        base_path + '.gif',
                    ]
                    
                    found = False
                    for possible_path in possible_paths:
                        if os.path.exists(possible_path):
                            local_path = possible_path
                            found = True
                            break
                    
                    if not found:
                        self.stdout.write(self.style.ERROR(f"  ❌ Local file not found: {local_path}"))
                        error_count += 1
                        continue

                self.stdout.write(f"  📂 Local path: {local_path}")

                if not dry_run:
                    # Upload to Cloudinary
                    self.stdout.write(f"  ☁️  Uploading to Cloudinary...")
                    
                    # Upload with original folder structure
                    folder_path = os.path.dirname(product.image.name)  # e.g., "products/2025/12"
                    
                    upload_result = cloudinary.uploader.upload(
                        local_path,
                        folder=folder_path,
                        public_id=os.path.splitext(os.path.basename(product.image.name))[0],  # filename without extension
                        resource_type="image",
                        overwrite=True,
                        invalidate=True
                    )

                    cloudinary_url = upload_result.get('secure_url')
                    cloudinary_public_id = upload_result.get('public_id')

                    self.stdout.write(self.style.SUCCESS(f"  ✅ Uploaded to Cloudinary!"))
                    self.stdout.write(f"     Public ID: {cloudinary_public_id}")
                    self.stdout.write(f"     URL: {cloudinary_url}")

                    # Update product with Cloudinary path
                    product.image = cloudinary_public_id
                    product.save(update_fields=['image'])

                    self.stdout.write(self.style.SUCCESS(f"  💾 Updated product record"))
                    success_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f"  🔍 Would upload: {local_path}"))
                    success_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Error: {str(e)}"))
                error_count += 1

        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(f"\n✅ Successfully migrated: {success_count}")
        self.stdout.write(f"⏭️  Skipped (already on Cloudinary): {skipped_count}")
        self.stdout.write(f"❌ Errors: {error_count}")
        self.stdout.write(f"📊 Total processed: {total_products}\n")

        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 This was a DRY RUN - no changes were made'))
            self.stdout.write(self.style.WARNING('Run without --dry-run to actually migrate images\n'))
        else:
            self.stdout.write(self.style.SUCCESS('\n🎉 Migration complete!\n'))