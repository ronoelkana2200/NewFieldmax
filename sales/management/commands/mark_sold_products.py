from django.core.management.base import BaseCommand
from django.db import transaction
from sales.models import Sale
from inventory.models import Product


class Command(BaseCommand):
    help = 'Mark all products from existing active sales as SOLD'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Starting to mark sold products...'))
        
        # Get all active (non-reversed) sales
        active_sales = Sale.objects.filter(is_reversed=False).select_related('product', 'product__category')
        
        total_sales = active_sales.count()
        self.stdout.write(f"Found {total_sales} active sales")
        
        updated_count = 0
        single_items_updated = 0
        bulk_items_updated = 0
        already_sold = 0
        
        with transaction.atomic():
            for sale in active_sales:
                product = sale.product
                
                # Skip if already marked as sold
                if product.status == 'sold':
                    already_sold += 1
                    continue
                
                # For single items: mark as sold
                if product.category.is_single_item:
                    product.quantity = 0
                    product.status = 'sold'
                    product.save(update_fields=['quantity', 'status'])
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Marked single item as SOLD: {product.product_code} "
                            f"(Sale #{sale.sale_id})"
                        )
                    )
                    single_items_updated += 1
                    updated_count += 1
                
                # For bulk items: just update status based on quantity
                else:
                    old_status = product.status
                    product._update_status()  # Recalculate status
                    
                    if old_status != product.status:
                        product.save(update_fields=['status'])
                        self.stdout.write(
                            f"✓ Updated bulk item status: {product.product_code} "
                            f"({old_status} → {product.status})"
                        )
                        bulk_items_updated += 1
                        updated_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('SUMMARY:'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(f"Total active sales: {total_sales}")
        self.stdout.write(f"Single items marked as SOLD: {single_items_updated}")
        self.stdout.write(f"Bulk items updated: {bulk_items_updated}")
        self.stdout.write(f"Already marked as sold: {already_sold}")
        self.stdout.write(f"Total products updated: {updated_count}")
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('\n✅ Done!'))
