from django.apps import AppConfig


class InventoryConfig(AppConfig):
    """
    Configuration for the Inventory application.
    
    This app manages product inventory including:
    - Categories (Single items like phones, Bulk items like cables)
    - Products (with unique product codes and SKU values)
    - Stock Entries (purchases, sales, returns, adjustments)
    
    Features:
    - Automatic product code generation (e.g., PFSL001, AFSL001)
    - Automatic status updates based on quantity
    - Stock movement tracking with audit trail
    - Single item vs Bulk item management
    - IMEI/Serial Number/Barcode support
    """
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'
    verbose_name = 'Inventory Management'
    
    def ready(self):
        """
        Import signal handlers when the app is ready.
        
        Signals handle:
        - Automatic SKU stock quantity updates when StockEntry is created
        - Product status updates based on quantity changes
        - Audit trail maintenance
        """
        import inventory.signals  # noqa: F401