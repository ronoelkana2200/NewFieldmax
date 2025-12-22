# sales/admin.py - FULL DELETE PERMISSIONS FOR ALL TABLES

from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import reverse
from django.db import transaction
from decimal import Decimal

from .models import Sale, SaleItem, SaleReversal, FiscalReceipt
from .forms import SaleAdminForm, SaleItemInlineForm


# ============================================
# INLINE ADMIN FOR SALE ITEMS
# ============================================

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    form = SaleItemInlineForm
    extra = 0
    
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
        if obj and obj.etr_status == 'processed':
            return False
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Allow superusers to delete, restrict staff from deleting processed sale items"""
        if request.user.is_superuser:
            return True
        if obj and obj.etr_status == 'processed':
            return False
        return super().has_delete_permission(request, obj)


# ============================================
# MAIN SALE ADMIN - FULL DELETE PERMISSIONS
# ============================================

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
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
    
    # Register admin actions
    actions = ['generate_etr_receipts_action', 'safe_delete_sales_action']
    
    # ============================================
    # DELETE PERMISSIONS - ALLOW SUPERUSER
    # ============================================
    
    def has_delete_permission(self, request, obj=None):
        """
        Allow superusers to delete any sale
        Prevent staff from deleting processed sales
        """
        if request.user.is_superuser:
            return True
        
        # For staff users, prevent deletion of processed sales
        if obj and obj.etr_status == 'processed':
            return False
        
        return super().has_delete_permission(request, obj)
    
    def delete_model(self, request, obj):
        """
        Override delete_model to handle cascading deletes properly
        This is called when deleting a single object
        """
        if request.user.is_superuser:
            with transaction.atomic():
                sale_id = obj.sale_id
                
                # Delete related objects first
                items_deleted = obj.items.all().delete()
                
                fiscal_deleted = 0
                if hasattr(obj, 'fiscal_receipt'):
                    obj.fiscal_receipt.delete()
                    fiscal_deleted = 1
                
                reversal_deleted = 0
                if hasattr(obj, 'reversal'):
                    obj.reversal.delete()
                    reversal_deleted = 1
                
                # Now delete the sale
                obj.delete()
                
            self.message_user(
                request,
                f"Sale {sale_id} deleted successfully. "
                f"(Items: {items_deleted[0]}, Fiscal: {fiscal_deleted}, Reversals: {reversal_deleted})",
                messages.SUCCESS
            )
        else:
            super().delete_model(request, obj)
    
    def delete_queryset(self, request, queryset):
        """
        Override delete_queryset to handle bulk deletion
        This is called when using the admin action
        """
        if request.user.is_superuser:
            deleted_count = 0
            total_items = 0
            total_fiscal = 0
            total_reversals = 0
            
            with transaction.atomic():
                for sale in queryset:
                    # Delete related objects
                    items_count = sale.items.count()
                    sale.items.all().delete()
                    total_items += items_count
                    
                    if hasattr(sale, 'fiscal_receipt'):
                        sale.fiscal_receipt.delete()
                        total_fiscal += 1
                    
                    if hasattr(sale, 'reversal'):
                        sale.reversal.delete()
                        total_reversals += 1
                    
                    # Delete the sale
                    sale.delete()
                    deleted_count += 1
            
            self.message_user(
                request,
                f"Successfully deleted {deleted_count} sale(s), "
                f"{total_items} item(s), {total_fiscal} fiscal receipt(s), "
                f"and {total_reversals} reversal(s).",
                messages.SUCCESS
            )
        else:
            super().delete_queryset(request, queryset)
    
    # ============================================
    # DISPLAY METHODS
    # ============================================
    
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
    
    # ============================================
    # ADMIN ACTIONS
    # ============================================
    
    @admin.action(description='Generate ETR receipts for selected sales')
    def generate_etr_receipts_action(self, request, queryset):
        """Batch generate ETR receipts"""
        count = 0
        for sale in queryset.filter(etr_receipt_number__isnull=True):
            sale.assign_etr_receipt_number()
            count += 1
        
        self.message_user(
            request,
            f'Generated {count} ETR receipt(s)',
            messages.SUCCESS
        )
    
    @admin.action(description="Delete selected sales (Superuser only)")
    def safe_delete_sales_action(self, request, queryset):
        """Safe deletion with proper cascade handling"""
        if not request.user.is_superuser:
            self.message_user(
                request,
                "Only superusers can delete sales.",
                messages.ERROR
            )
            return
        
        deleted_count = 0
        total_items = 0
        total_fiscal = 0
        total_reversals = 0
        
        with transaction.atomic():
            for sale in queryset:
                # Delete related objects
                items_count = sale.items.count()
                sale.items.all().delete()
                total_items += items_count
                
                if hasattr(sale, 'fiscal_receipt'):
                    sale.fiscal_receipt.delete()
                    total_fiscal += 1
                
                if hasattr(sale, 'reversal'):
                    sale.reversal.delete()
                    total_reversals += 1
                
                # Delete the sale
                sale.delete()
                deleted_count += 1
        
        self.message_user(
            request,
            f"Successfully deleted {deleted_count} sale(s), "
            f"{total_items} item(s), {total_fiscal} fiscal receipt(s), "
            f"and {total_reversals} reversal(s).",
            messages.SUCCESS
        )


# ============================================
# SALE ITEM ADMIN - ALLOW DELETE
# ============================================

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = [
        'id',
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
    
    # Register delete action
    actions = ['delete_selected_items']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow superusers to delete sale items"""
        return request.user.is_superuser
    
    def delete_model(self, request, obj):
        """Override to provide feedback on deletion"""
        sale_id = obj.sale.sale_id
        product_name = obj.product_name
        
        with transaction.atomic():
            obj.delete()
        
        self.message_user(
            request,
            f"Sale Item deleted: {product_name} from Sale #{sale_id}",
            messages.SUCCESS
        )
    
    def delete_queryset(self, request, queryset):
        """Handle bulk deletion"""
        if request.user.is_superuser:
            count = queryset.count()
            
            with transaction.atomic():
                queryset.delete()
            
            self.message_user(
                request,
                f"Successfully deleted {count} sale item(s).",
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                "Only superusers can delete sale items.",
                messages.ERROR
            )
    
    @admin.action(description="Delete selected sale items")
    def delete_selected_items(self, request, queryset):
        """Custom delete action"""
        if not request.user.is_superuser:
            self.message_user(
                request,
                "Only superusers can delete sale items.",
                messages.ERROR
            )
            return
        
        count = queryset.count()
        
        with transaction.atomic():
            queryset.delete()
        
        self.message_user(
            request,
            f"Successfully deleted {count} sale item(s).",
            messages.SUCCESS
        )
    
    def sale_link(self, obj):
        url = reverse('admin:sales_sale_change', args=[obj.sale.sale_id])
        return format_html('<a href="{}">Sale #{}</a>', url, obj.sale.sale_id)
    sale_link.short_description = 'Sale'
    
    def unit_price_display(self, obj):
        return f'KSH {obj.unit_price:,.2f}'
    unit_price_display.short_description = 'Unit Price'
    
    def total_price_display(self, obj):
        return format_html(
            '<strong style="color: #10b981;">KSH {}</strong>',
            f"{float(obj.total_price):,.2f}"
        )
    total_price_display.short_description = 'Total'


# ============================================
# SALE REVERSAL ADMIN - ALLOW DELETE
# ============================================

@admin.register(SaleReversal)
class SaleReversalAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'sale_link',
        'reversed_at',
        'reversed_by',
        'reason_preview',
    ]
    
    list_filter = ['reversed_at', 'reversed_by']
    search_fields = ['sale__sale_id', 'reason']
    readonly_fields = ['sale', 'reversed_at', 'reversed_by', 'reason']
    
    # Register delete action
    actions = ['delete_selected_reversals']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow superusers to delete sale reversals"""
        return request.user.is_superuser
    
    def delete_model(self, request, obj):
        """Override to provide feedback on deletion"""
        sale_id = obj.sale.sale_id
        
        with transaction.atomic():
            obj.delete()
        
        self.message_user(
            request,
            f"Sale Reversal deleted for Sale #{sale_id}",
            messages.SUCCESS
        )
    
    def delete_queryset(self, request, queryset):
        """Handle bulk deletion"""
        if request.user.is_superuser:
            count = queryset.count()
            
            with transaction.atomic():
                queryset.delete()
            
            self.message_user(
                request,
                f"Successfully deleted {count} sale reversal(s).",
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                "Only superusers can delete sale reversals.",
                messages.ERROR
            )
    
    @admin.action(description="Delete selected reversals")
    def delete_selected_reversals(self, request, queryset):
        """Custom delete action"""
        if not request.user.is_superuser:
            self.message_user(
                request,
                "Only superusers can delete sale reversals.",
                messages.ERROR
            )
            return
        
        count = queryset.count()
        
        with transaction.atomic():
            queryset.delete()
        
        self.message_user(
            request,
            f"Successfully deleted {count} sale reversal(s).",
            messages.SUCCESS
        )
    
    def sale_link(self, obj):
        url = reverse('admin:sales_sale_change', args=[obj.sale.sale_id])
        return format_html('<a href="{}">Sale #{}</a>', url, obj.sale.sale_id)
    sale_link.short_description = 'Sale'
    
    def reason_preview(self, obj):
        if obj.reason:
            return obj.reason[:50] + '...' if len(obj.reason) > 50 else obj.reason
        return '—'
    reason_preview.short_description = 'Reason'


# ============================================
# FISCAL RECEIPT ADMIN - ALLOW DELETE
# ============================================

@admin.register(FiscalReceipt)
class FiscalReceiptAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'receipt_number',
        'sale_link',
        'issued_at',
        'verification_url_display',
    ]
    
    list_filter = ['issued_at']
    search_fields = ['receipt_number', 'sale__sale_id']
    readonly_fields = [
        'sale',
        'receipt_number',
        'issued_at',
        'qr_code',
        'verification_url',
    ]
    
    # Register delete action
    actions = ['delete_selected_receipts']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow superusers to delete fiscal receipts"""
        return request.user.is_superuser
    
    def delete_model(self, request, obj):
        """Override to provide feedback on deletion"""
        receipt_number = obj.receipt_number
        sale_id = obj.sale.sale_id
        
        with transaction.atomic():
            obj.delete()
        
        self.message_user(
            request,
            f"Fiscal Receipt {receipt_number} deleted (Sale #{sale_id})",
            messages.SUCCESS
        )
    
    def delete_queryset(self, request, queryset):
        """Handle bulk deletion"""
        if request.user.is_superuser:
            count = queryset.count()
            
            with transaction.atomic():
                queryset.delete()
            
            self.message_user(
                request,
                f"Successfully deleted {count} fiscal receipt(s).",
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                "Only superusers can delete fiscal receipts.",
                messages.ERROR
            )
    
    @admin.action(description="Delete selected fiscal receipts")
    def delete_selected_receipts(self, request, queryset):
        """Custom delete action"""
        if not request.user.is_superuser:
            self.message_user(
                request,
                "Only superusers can delete fiscal receipts.",
                messages.ERROR
            )
            return
        
        count = queryset.count()
        
        with transaction.atomic():
            queryset.delete()
        
        self.message_user(
            request,
            f"Successfully deleted {count} fiscal receipt(s).",
            messages.SUCCESS
        )
    
    def sale_link(self, obj):
        url = reverse('admin:sales_sale_change', args=[obj.sale.sale_id])
        return format_html('<a href="{}">Sale #{}</a>', url, obj.sale.sale_id)
    sale_link.short_description = 'Sale'
    
    def verification_url_display(self, obj):
        if obj.verification_url:
            return format_html(
                '<a href="{}" target="_blank">Verify</a>',
                obj.verification_url
            )
        return '—'
    verification_url_display.short_description = 'Verification'


# ============================================
# ADMIN CUSTOMIZATION SUMMARY
# ============================================

"""
DELETE PERMISSIONS ENABLED FOR ALL TABLES:

✅ Sales (admin.sales_sale)
   - Superusers can delete
   - Staff cannot delete processed sales
   - Cascade deletes: Items, Fiscal Receipts, Reversals

✅ Sale Items (admin.sales_saleitem)
   - Superusers can delete
   - Staff cannot delete
   - Individual and bulk deletion supported

✅ Sale Reversals (admin.sales_salereversal)
   - Superusers can delete
   - Staff cannot delete
   - Individual and bulk deletion supported

✅ Fiscal Receipts (admin.sales_fiscalreceipt)
   - Superusers can delete
   - Staff cannot delete
   - Individual and bulk deletion supported

FEATURES:
- Transaction-safe deletions
- Detailed success messages
- Bulk delete actions
- Proper cascade handling
- Permission checks
"""