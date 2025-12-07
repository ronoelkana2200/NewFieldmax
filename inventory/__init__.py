"""
Inventory Management Application

This Django app provides comprehensive inventory management with support for:

FEATURES:
- Single Items: Unique products (phones) with individual IMEI/Serial numbers
- Bulk Items: Stock products (accessories) with shared identifiers
- Automatic product code generation (e.g., PFSL001, AFSL002)
- Stock movement tracking (purchases, sales, returns, adjustments)
- Automatic status updates based on quantity
- Complete audit trail for all inventory movements
- Low stock alerts and notifications
- REST API endpoints for integration
- Beautiful admin interface with color coding

MODELS:
- Category: Product categories with item type (single/bulk) and SKU type
- Product: Individual products with unique codes and SKU values
- StockEntry: All inventory movements with complete audit trail

BUSINESS LOGIC:
Single Items:
  - Each unit = separate Product record with unique product_code
  - Each has unique SKU (IMEI/Serial Number)
  - Quantity always 0 or 1
  - Cannot be restocked (only returned)
  - Status: 'available' or 'sold'

Bulk Items:
  - Multiple units share one Product record
  - All units share same SKU (Serial/Barcode)
  - Quantity can be any positive number
  - Can be restocked
  - Status: 'available', 'lowstock', or 'outofstock'

USAGE:
    # Import models
    from inventory.models import Category, Product, StockEntry
    
    # Create category
    phones = Category.objects.create(
        name="Phones",
        item_type="single",
        sku_type="imei"
    )
    
    # Create single item product
    phone = Product.objects.create(
        name="Samsung S24",
        category=phones,
        sku_value="IMEI:234234234000",
        buying_price=800,
        selling_price=1000
    )  # Auto-generates product_code: PFSL001
    
    # Record sale
    StockEntry.objects.create(
        product=phone,
        quantity=-1,
        entry_type='sale',
        unit_price=1000,
        total_amount=1000
    )  # Auto-updates product.quantity and status

VERSION: 2.0.0
AUTHOR: Your Team
LICENSE: Proprietary
"""

default_app_config = 'inventory.apps.InventoryConfig'

__version__ = '2.0.0'
__author__ = 'Your Team'

# Version history:
# 2.0.0 - Removed SKU model, simplified to product-centric design
# 1.0.0 - Initial release with separate SKU model