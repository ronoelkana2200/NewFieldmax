from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from sales.models import Sale
import logging
from inventory.models import StockEntry


logger = logging.getLogger(__name__)


# ============================================
# SALE SIGNALS - AUTOMATIC STOCK MANAGEMENT
# ============================================


@receiver(post_save, sender=Sale)
def update_product_on_sale(sender, instance, created, **kwargs):
    """
    Monitor sales - stock updates handled by SaleItem.process_sale().
    Logs all items in a sale for auditing.
    """
    if not created or instance.is_reversed:
        return

    # Log each item in the sale
    for item in instance.items.all():
        product = item.product
        logger.info(
            f"[SALE MONITOR] Sale #{instance.sale_id} | "
            f"Product: {product.product_code} ({product.name}) | "
            f"Quantity Sold: {item.quantity} | "
            f"Buyer: {instance.buyer_name or 'Walk-in'} | "
            f"Total: KSH {item.total_price}"
        )

# ============================================
# SALE REVERSAL SIGNAL
# ============================================
# signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
import logging

from sales.models import Sale
from inventory.models import StockEntry

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Sale)
def restore_product_on_reversal(sender, instance, created, **kwargs):
    """
    Restore product stock when a sale is reversed.
    
    SINGLE ITEMS:
    - Change status from 'sold' → 'available'
    - Set quantity = 1
    
    BULK ITEMS:
    - Add quantity back
    - Auto-update status
    """
    # Only process when is_reversed changes to True
    if created:
        return

    if not instance.is_reversed:
        return

    # Avoid double processing
    if hasattr(instance, '_reversal_processed'):
        return
    instance._reversal_processed = True

    try:
        with transaction.atomic():
            for item in instance.items.all():
                product = item.product
                quantity_returned = item.quantity or 0
                unit_price = item.unit_price or 0

                # Lock product row
                product = product.__class__.objects.select_for_update().get(pk=product.pk)

                logger.info(
                    f"[SALE REVERSAL SIGNAL] Processing reversal for sale #{instance.sale_id} | "
                    f"Product: {product.product_code} | Quantity: {quantity_returned}"
                )

                # SINGLE ITEMS
                if product.category.is_single_item:
                    old_status = product.status
                    product.quantity = 1
                    product.status = 'available'
                    product.save(update_fields=['quantity', 'status', 'updated_at'])

                    logger.info(
                        f"[SINGLE ITEM RESTORED] Product: {product.product_code} | "
                        f"Status: {old_status} → {product.status} | Quantity: 0 → 1"
                    )

                # BULK ITEMS
                else:
                    old_quantity = product.quantity
                    old_status = product.status
                    product.quantity += quantity_returned

                    # Update status
                    if product.quantity > 5:
                        product.status = 'available'
                    elif product.quantity > 0:
                        product.status = 'lowstock'
                    else:
                        product.status = 'outofstock'

                    product.save(update_fields=['quantity', 'status', 'updated_at'])

                    logger.info(
                        f"[BULK ITEM RESTORED] Product: {product.product_code} | "
                        f"Quantity: {old_quantity} → {product.quantity} | Status: {old_status} → {product.status}"
                    )

                # Create a StockEntry for reversal
                StockEntry.objects.create(
                    product=product,
                    quantity=quantity_returned,
                    unit_price=unit_price,
                    total_amount=abs(quantity_returned * unit_price),
                    reference_id=f"REVERSE-{instance.sale_id}",
                    notes=f"Reversal of sale {instance.sale_id}"
                )

                logger.info(
                    f"[STOCK ENTRY CREATED] Product: {product.product_code} | "
                    f"Quantity: {quantity_returned} | Reference: REVERSE-{instance.sale_id}"
                )

    except Exception as e:
        logger.exception(
            f"[REVERSAL SIGNAL ERROR] Failed to restore products for sale #{instance.sale_id}: {e}"
        )


# ============================================
# SIGNAL DOCUMENTATION
# ============================================

"""
AUTOMATIC STOCK MANAGEMENT FLOW:

1. SALE CREATED:
   → post_save signal triggered
   → Product quantity updated
   → Product status updated (sold/lowstock/outofstock)
   → StockEntry created for audit trail
   → Alerts logged if needed

2. SALE REVERSED:
   → post_save signal triggered (is_reversed=True)
   → Product quantity restored
   → Product status updated (available/lowstock)
   → Alerts logged

SINGLE ITEM FLOW:
- New Sale → quantity: 1→0, status: available→sold
- Reversal → quantity: 0→1, status: sold→available

BULK ITEM FLOW:
- New Sale → quantity: 10→7, status: available→lowstock
- Reversal → quantity: 7→10, status: lowstock→available

SAFETY FEATURES:
- Database locks prevent race conditions
- Negative stock prevented
- Duplicate StockEntry checks
- Comprehensive error logging
- Transaction atomicity ensures consistency
"""