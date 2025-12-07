# sales/admin.py - FIXED VERSION

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from decimal import Decimal

from .models import Sale, SaleItem, SaleReversal, FiscalReceipt
from .forms import SaleAdminForm, SaleItemInlineForm


# ============================================
# INLINE ADMIN FOR SALE ITEMS
# ============================================

class SaleItemInline(admin.TabularInline):
    """
    Display sale items inline within Sale admin
    """
    model = SaleItem
    form = SaleItemInlineForm
    extra = 0  # No empty forms by default
    
    fields = [
        'product',
        'product_code',
        'product_name',
        'sku_value',
        'quantity',
        'unit_price',
        'total_price',
    ]
    
    readonly_fields = [
        'product_code',
        'product_name',
        'sku_value',
        'total_price',
    ]
    
    def has_add_permission(self, request, obj=None):
        # Prevent adding items to already processed sales
        if obj and obj.etr_status == 'processed':
            return False
        return True
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deleting items from processed sales
        if obj and obj.etr_status == 'processed':
            return False
        return True


# ============================================
# MAIN SALE ADMIN
# ============================================

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    """
    Admin interface for Sale model
    ✅ FIXED: Shows transaction-level view with items inline
    """
    
    form = SaleAdminForm
    inlines = [SaleItemInline]
    
    list_display = [
        'sale_id',
        'seller_name',
        'item_count_display',
        'total_amount_display',
        'buyer_name',
        'etr_receipt_display',
        'etr_status_badge',
        'sale_date',
        'reversal_status',
    ]
    
    list_filter = [
        'etr_status',
        'is_reversed',
        'sale_date',
        'seller',
    ]
    
    search_fields = [
        'sale_id',
        'etr_receipt_number',
        'fiscal_receipt_number',
        'buyer_name',
        'buyer_phone',
        'buyer_id_number',
    ]
    
    readonly_fields = [
        'sale_id',
        'total_quantity',
        'subtotal',
        'total_amount',
        'etr_receipt_number',
        'etr_receipt_counter',
        'etr_processed_at',
        'reversed_at',
        'reversed_by',
        'sale_date',
        'receipt_link',
    ]
    
    fieldsets = (
        ('Transaction Info', {
            'fields': (
                'sale_id',
                'seller',
                'sale_date',
                'etr_status',
            )
        }),
        ('Totals', {
            'fields': (
                'total_quantity',
                'subtotal',
                'tax_amount',
                'total_amount',
            ),
            'description': 'Automatically calculated from items'
        }),
        ('Customer Details', {
            'fields': (
                'buyer_name',
                'buyer_phone',
                'buyer_id_number',
                'nok_name',
                'nok_phone',
            ),
            'classes': ('collapse',)
        }),
        ('Receipt Information', {
            'fields': (
                'etr_receipt_number',
                'etr_receipt_counter',
                'fiscal_receipt_number',
                'etr_processed_at',
                'receipt_link',
            )
        }),
        ('Reversal Information', {
            'fields': (
                'is_reversed',
                'reversed_at',
                'reversed_by',
                'reversal_reason',
            ),
            'classes': ('collapse',)
        }),
    )
    
    def seller_name(self, obj):
        return obj.seller.get_full_name() if obj.seller else 'N/A'
    seller_name.short_description = 'Seller'
    
    def item_count_display(self, obj):
        count = obj.items.count()
        return format_html(
            '<strong>{}</strong> item{}',
            count,
            's' if count != 1 else ''
        )
    item_count_display.short_description = 'Items'
    

    def total_amount_display(self, obj):
        amount = f"{float(obj.total_amount):,.2f}"
        return format_html(
            '<strong style="color: #10b981;">KSH {}</strong>',
            amount
        )

    total_amount_display.short_description = 'Total'
    total_amount_display.admin_order_field = 'total_amount'
    
    def etr_receipt_display(self, obj):
        if obj.etr_receipt_number:
            return format_html(
                '<code style="background: #f3f4f6; padding: 2px 6px; border-radius: 3px;">{}</code>',
                obj.etr_receipt_number
            )
        return format_html('<span style="color: #9ca3af;">—</span>')
    etr_receipt_display.short_description = 'Receipt No.'
    
    def etr_status_badge(self, obj):
        colors = {
            'pending': '#fbbf24',
            'processed': '#10b981',
            'failed': '#ef4444'
        }
        color = colors.get(obj.etr_status, '#6b7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.etr_status.upper()
        )
    etr_status_badge.short_description = 'ETR Status'
    
    def reversal_status(self, obj):
        if obj.is_reversed:
            return format_html(
                '<span style="color: #ef4444; font-weight: bold;">✗ REVERSED</span>'
            )
        return format_html(
            '<span style="color: #10b981;">✓ Active</span>'
        )
    reversal_status.short_description = 'Status'
    
    def receipt_link(self, obj):
        if obj.etr_receipt_number:
            url = reverse('sales:sale-receipt', args=[obj.sale_id])
            return format_html(
                '<a href="{}" target="_blank" class="button">View Receipt</a>',
                url
            )
        return '—'
    receipt_link.short_description = 'Receipt'
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of processed sales
        if obj and obj.etr_status == 'processed':
            return False
        return super().has_delete_permission(request, obj)


# ============================================
# SALE ITEM ADMIN (Optional standalone view)
# ============================================

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    """
    Standalone admin for viewing all sale items
    Useful for inventory tracking and reports
    """
    
    list_display = [
        'sale_link',
        'product_name',
        'sku_value',
        'quantity',
        'unit_price_display',
        'total_price_display',
        'created_at',
    ]
    
    list_filter = [
        'created_at',
        'product__category',
    ]
    
    search_fields = [
        'sale__sale_id',
        'product_code',
        'product_name',
        'sku_value',
    ]
    
    readonly_fields = [
        'sale',
        'product',
        'product_code',
        'product_name',
        'sku_value',
        'quantity',
        'unit_price',
        'total_price',
        'created_at',
        'product_age_days',
    ]
    
    def has_add_permission(self, request):
        # Items should only be added through Sale admin
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of processed sale items
        if obj and obj.sale.etr_status == 'processed':
            return False
        return True
    
    def sale_link(self, obj):
        url = reverse('admin:sales_sale_change', args=[obj.sale.sale_id])
        return format_html(
            '<a href="{}">Sale #{}</a>',
            url,
            obj.sale.sale_id
        )
    sale_link.short_description = 'Sale'
    
    def unit_price_display(self, obj):
        return f'KSH {obj.unit_price:,.2f}'
    unit_price_display.short_description = 'Unit Price'
    unit_price_display.admin_order_field = 'unit_price'
    
    def total_price_display(self, obj):
        amount = f"{float(obj.total_price):,.2f}"
        return format_html(
            '<strong style="color: #10b981;">KSH {}</strong>',
            amount
        )

    total_price_display.short_description = 'Total'
    total_price_display.admin_order_field = 'total_price'


# ============================================
# SALE REVERSAL ADMIN
# ============================================

@admin.register(SaleReversal)
class SaleReversalAdmin(admin.ModelAdmin):
    """
    Admin for viewing sale reversals
    """
    
    list_display = [
        'sale_link',
        'reversed_at',
        'reversed_by',
        'reason_preview',
    ]
    
    list_filter = [
        'reversed_at',
        'reversed_by',
    ]
    
    search_fields = [
        'sale__sale_id',
        'reason',
    ]
    
    readonly_fields = [
        'sale',
        'reversed_at',
        'reversed_by',
        'reason',
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def sale_link(self, obj):
        url = reverse('admin:sales_sale_change', args=[obj.sale.sale_id])
        return format_html(
            '<a href="{}">Sale #{}</a>',
            url,
            obj.sale.sale_id
        )
    sale_link.short_description = 'Sale'
    
    def reason_preview(self, obj):
        if obj.reason:
            return obj.reason[:50] + '...' if len(obj.reason) > 50 else obj.reason
        return '—'
    reason_preview.short_description = 'Reason'


# ============================================
# FISCAL RECEIPT ADMIN
# ============================================

@admin.register(FiscalReceipt)
class FiscalReceiptAdmin(admin.ModelAdmin):
    """
    Admin for fiscal receipts
    """
    
    list_display = [
        'receipt_number',
        'sale_link',
        'issued_at',
        'validity_status',
    ]
    
    list_filter = [
        'issued_at',
    ]
    
    search_fields = [
        'receipt_number',
        'sale__sale_id',
    ]
    
    readonly_fields = [
        'sale',
        'receipt_number',
        'issued_at',
        'qr_code',
        'verification_url',
    ]
    
    def has_add_permission(self, request):
        return False
    
    def sale_link(self, obj):
        url = reverse('admin:sales_sale_change', args=[obj.sale.sale_id])
        return format_html(
            '<a href="{}">Sale #{}</a>',
            url,
            obj.sale.sale_id
        )
    sale_link.short_description = 'Sale'
    
    def validity_status(self, obj):
        if obj.is_valid:
            return format_html(
                '<span style="color: #10b981; font-weight: bold;">✓ Valid</span>'
            )
        return format_html(
            '<span style="color: #ef4444; font-weight: bold;">✗ Invalid (Reversed)</span>'
        )
    validity_status.short_description = 'Status'


# ============================================
# ADMIN ACTIONS
# ============================================

@admin.action(description='Generate ETR receipts for selected sales')
def generate_etr_receipts(modeladmin, request, queryset):
    """Batch generate ETR receipts"""
    count = 0
    for sale in queryset.filter(etr_receipt_number__isnull=True):
        sale.assign_etr_receipt_number()
        count += 1
    
    modeladmin.message_user(
        request,
        f'Generated {count} ETR receipt(s)'
    )

# Add action to SaleAdmin
SaleAdmin.actions = [generate_etr_receipts]