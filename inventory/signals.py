from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from .models import Product, StockEntry
import logging

logger = logging.getLogger(__name__)


# ============================================
# PRODUCT SIGNALS
# ============================================

@receiver(pre_save, sender=Product)
def product_pre_save(sender, instance, **kwargs):
    """
    Handle product before saving.
    
    Actions:
    - Generate product_code if not exists
    - Enforce single item quantity = 1
    - Update status based on quantity
    """
    # These are already handled in the model's save() method
    # This signal is here for any additional pre-save logic you might need
    
    # Log product creation
    if not instance.pk:
        logger.info(f"Creating new product: {instance.name}")


@receiver(post_save, sender=Product)
def product_post_save(sender, instance, created, **kwargs):
    """
    Handle product after saving.
    
    Actions:
    - Log product creation/updates
    - Send notifications (if needed)
    """
    if created:
        logger.info(
            f"Product created: {instance.product_code} - {instance.name} "
            f"(Category: {instance.category.name}, Quantity: {instance.quantity})"
        )
    else:
        logger.debug(
            f"Product updated: {instance.product_code} - {instance.name} "
            f"(Status: {instance.status}, Quantity: {instance.quantity})"
        )


# ============================================
# STOCK ENTRY SIGNALS
# ============================================

@receiver(post_save, sender=StockEntry)
def update_product_on_stock_entry(sender, instance, created, **kwargs):
    """
    Update product quantity when stock entry is created.
    
    This is a safety net - the actual update happens in StockEntry.save()
    but this signal ensures consistency.
    
    Actions:
    - Verify product quantity matches stock movements
    - Log stock movements
    """
    if created:
        product = instance.product
        
        # Log the stock movement
        direction = "IN" if instance.is_stock_in else "OUT"
        logger.info(
            f"Stock {direction}: {instance.get_entry_type_display()} - "
            f"Product: {product.product_code} - "
            f"Quantity: {instance.quantity} - "
            f"New Stock: {product.quantity}"
        )
        
        # Validate stock consistency (warning only, don't fail)
        if product.quantity < 0:
            logger.warning(
                f"NEGATIVE STOCK ALERT: Product {product.product_code} "
                f"has negative quantity: {product.quantity}"
            )
    if instance.entry_type == 'initial_load':
        logger.info("Skipping stock quantity update for initial product load")
        return

@receiver(pre_save, sender=StockEntry)
def stock_entry_pre_save(sender, instance, **kwargs):
    """
    Validate stock entry before saving.
    
    Actions:
    - Calculate total_amount if not provided
    - Log entry creation
    """
    # Calculate total_amount if not set
    if not instance.total_amount and instance.unit_price:
        instance.total_amount = abs(instance.quantity) * instance.unit_price
    
    if not instance.pk:
        logger.debug(
            f"Creating stock entry: {instance.entry_type} - "
            f"Product: {instance.product.product_code} - "
            f"Quantity: {instance.quantity}"
        )


# ============================================
# LOW STOCK ALERTS (OPTIONAL)
# ============================================

@receiver(post_save, sender=Product)
def check_low_stock_alert(sender, instance, **kwargs):
    """
    Send alerts when products reach low stock levels.
    
    You can extend this to:
    - Send email notifications
    - Create admin notifications
    - Trigger reorder processes
    - Send SMS alerts
    """
    # Only for bulk items
    if instance.category.is_bulk_item:
        # Low stock threshold
        if instance.status == 'lowstock':
            logger.warning(
                f"LOW STOCK ALERT: {instance.name} ({instance.product_code}) "
                f"has only {instance.quantity} units remaining"
            )
            
            # TODO: Send email/notification
            # send_low_stock_notification(instance)
        
        # Out of stock
        elif instance.status == 'outofstock':
            logger.error(
                f"OUT OF STOCK: {instance.name} ({instance.product_code}) "
                f"is out of stock"
            )
            
            # TODO: Send urgent notification
            # send_out_of_stock_notification(instance)


# ============================================
# AUDIT TRAIL SIGNALS
# ============================================

@receiver(post_save, sender=StockEntry)
def create_audit_trail(sender, instance, created, **kwargs):
    """
    Create audit trail for stock movements.
    
    This logs all stock movements to a separate audit log
    for compliance and reporting purposes.
    """
    if created:
        audit_message = (
            f"[STOCK MOVEMENT] "
            f"Type: {instance.get_entry_type_display()} | "
            f"Product: {instance.product.product_code} ({instance.product.name}) | "
            f"Quantity: {instance.quantity} | "
            f"Unit Price: ${instance.unit_price} | "
            f"Total: ${instance.total_amount} | "
            f"Reference: {instance.reference_id or 'N/A'} | "
            f"User: {instance.created_by.username if instance.created_by else 'System'} | "
            f"Timestamp: {instance.created_at}"
        )
        
        logger.info(audit_message)
        
        # TODO: Store in separate audit table if needed
        # AuditLog.objects.create(
        #     action='stock_movement',
        #     message=audit_message,
        #     user=instance.created_by,
        #     related_object=instance
        # )


# ============================================
# PREVENT STOCK ENTRY DELETION (OPTIONAL)
# ============================================

@receiver(post_delete, sender=StockEntry)
def log_stock_entry_deletion(sender, instance, **kwargs):
    """
    Log when stock entries are deleted (should be rare/never).
    
    Stock entries should not be deleted to maintain audit trail.
    This signal logs any deletions for security.
    """
    logger.warning(
        f"[AUDIT ALERT] Stock Entry DELETED: "
        f"ID: {instance.id} | "
        f"Type: {instance.entry_type} | "
        f"Product: {instance.product.product_code} | "
        f"Quantity: {instance.quantity} | "
        f"This should not happen in normal operations!"
    )
    
    # TODO: Send alert to administrators
    # send_admin_alert('Stock Entry Deleted', instance)


# ============================================
# CATEGORY CHANGE VALIDATION
# ============================================

@receiver(pre_save, sender=Product)
def validate_category_change(sender, instance, **kwargs):
    """
    Validate and handle category changes.
    
    Prevents changing from single to bulk (or vice versa)
    if it would cause data inconsistencies.
    """
    if instance.pk:  # Only for existing products
        try:
            old_product = Product.objects.get(pk=instance.pk)
            old_category = old_product.category
            new_category = instance.category
            
            # Check if category type changed
            if old_category.item_type != new_category.item_type:
                logger.warning(
                    f"Category type change detected for {instance.product_code}: "
                    f"{old_category.item_type} → {new_category.item_type}"
                )
                
                # Adjust quantity if changing to single item
                if new_category.is_single_item:
                    if instance.quantity > 1:
                        logger.warning(
                            f"Forcing quantity to 1 for {instance.product_code} "
                            f"(changed to single item category)"
                        )
                        instance.quantity = 1
                
        except Product.DoesNotExist:
            pass  # New product, no validation needed


# ============================================
# BULK OPERATIONS SIGNALS
# ============================================

@receiver(post_save, sender=Product)
def sync_related_data(sender, instance, created, **kwargs):
    """
    Sync related data when product is updated.
    
    This can be used to:
    - Update cached data
    - Trigger external API calls
    - Update related sales records
    """
    if not created:
        # Example: Update any cached product data
        # cache.delete(f'product_{instance.id}')
        pass


# ============================================
# NOTIFICATION HELPER FUNCTIONS
# ============================================

def send_low_stock_notification(product):
    """
    Send notification when product reaches low stock.
    
    Args:
        product: Product instance with low stock
    
    TODO: Implement actual notification logic:
    - Email to inventory manager
    - SMS alert
    - Dashboard notification
    - Slack/Teams message
    """
    logger.info(f"TODO: Send low stock notification for {product.product_code}")
    
    # Example implementation:
    # from django.core.mail import send_mail
    # send_mail(
    #     subject=f'Low Stock Alert: {product.name}',
    #     message=f'Product {product.product_code} has only {product.quantity} units left.',
    #     from_email='inventory@example.com',
    #     recipient_list=['manager@example.com'],
    # )


def send_out_of_stock_notification(product):
    """
    Send urgent notification when product is out of stock.
    
    Args:
        product: Product instance that's out of stock
    """
    logger.info(f"TODO: Send out of stock notification for {product.product_code}")


def send_admin_alert(subject, instance):
    """
    Send alert to administrators for critical events.
    
    Args:
        subject: Alert subject
        instance: Related model instance
    """
    logger.info(f"TODO: Send admin alert: {subject}")


# ============================================
# SIGNAL DOCUMENTATION
# ============================================

"""
Signal Flow for Stock Management:

1. PRODUCT CREATION:
   pre_save (Product) → Generate product_code, set quantity
   ↓
   save() → Product created in DB
   ↓
   post_save (Product) → Log creation, check stock levels

2. STOCK ENTRY CREATION:
   pre_save (StockEntry) → Calculate total_amount, validate
   ↓
   save() → StockEntry created, product.quantity updated
   ↓
   post_save (StockEntry) → Log movement, create audit trail
   ↓
   post_save (Product) → Check for low stock alerts

3. PRODUCT UPDATE:
   pre_save (Product) → Validate changes, update status
   ↓
   save() → Changes saved
   ↓
   post_save (Product) → Log update, sync related data

4. STOCK ENTRY DELETION (Should NOT happen):
   post_delete (StockEntry) → Log deletion, send alert

Notes:
- Signals should NOT modify the instance they're handling
  (except in pre_save if really necessary)
- Heavy operations should be queued (Celery tasks)
- All critical actions are logged
- Audit trail is maintained automatically
"""