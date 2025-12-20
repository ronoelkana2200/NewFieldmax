from django.contrib import admin
from .models import PendingOrder, PendingOrderItem

@admin.register(PendingOrder)
class PendingOrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'buyer_name', 'buyer_phone', 'total_amount', 
                    'status', 'created_at']
    list_filter = ['status', 'created_at', 'payment_method']
    search_fields = ['order_id', 'buyer_name', 'buyer_phone']
    readonly_fields = ['order_id', 'created_at', 'updated_at']
    
@admin.register(PendingOrderItem)
class PendingOrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product_name', 'quantity', 'unit_price', 'total_price']
    list_filter = ['created_at']
    search_fields = ['product_name', 'order__order_id']