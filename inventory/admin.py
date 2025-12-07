from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum
from decimal import Decimal
from django.http import HttpResponse
import csv

from .models import Category, Product, StockEntry

# ============================================
# CUSTOM ACTIONS
# ============================================

def export_to_csv(modeladmin, request, queryset):
    """Export selected items to CSV"""
    opts = modeladmin.model._meta
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename={opts.verbose_name_plural}.csv'

    writer = csv.writer(response)
    fields = [field for field in opts.get_fields() if not field.many_to_many and not field.one_to_many]

    # Write headers
    writer.writerow([field.verbose_name for field in fields])

    # Write data
    for obj in queryset:
        writer.writerow([getattr(obj, field.name) for field in fields])

    return response
export_to_csv.short_description = "Export to CSV"


def mark_as_active(modeladmin, request, queryset):
    queryset.update(is_active=True)
mark_as_active.short_description = "Mark as active"


def mark_as_inactive(modeladmin, request, queryset):
    queryset.update(is_active=False)
mark_as_inactive.short_description = "Mark as inactive"


# ============================================
# INLINE ADMINS
# ============================================

class StockEntryInline(admin.TabularInline):
    model = StockEntry
    extra = 0
    can_delete = False
    readonly_fields = [
        'quantity',
        'entry_type',
        'unit_price',
        'total_amount',
        'reference_id',
        'created_by',
        'created_at',
        'notes'
    ]
    fields = [
        'entry_type',
        'quantity',
        'unit_price',
        'total_amount',
        'reference_id',
        'created_by',
        'created_at'
    ]

    def has_add_permission(self, request, obj=None):
        return False


class ProductInline(admin.TabularInline):
    model = Product
    extra = 0
    fields = ['product_code', 'name', 'sku_value', 'quantity', 'status', 'is_active']
    readonly_fields = ['product_code', 'status']
    show_change_link = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(is_active=True)


# ============================================
# CATEGORY ADMIN
# ============================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'category_code',
        'item_type_badge',
        'sku_type_badge',
        'product_count',
        'total_inventory_value',
    ]
    list_filter = ['item_type', 'sku_type']
    search_fields = ['name', 'category_code']
    readonly_fields = ['category_code', 'created_info']
    fieldsets = (
        ('Basic Information', {'fields': ('name', 'category_code')}),
        ('Configuration', {'fields': ('item_type', 'sku_type')}),
        ('Statistics', {'fields': ('created_info',), 'classes': ('collapse',)}),
    )
    inlines = [ProductInline]
    actions = [export_to_csv]

    def item_type_badge(self, obj):
        colors = {'single': '#007bff', 'bulk': '#28a745'}
        color = colors.get(obj.item_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_item_type_display()
        )
    item_type_badge.short_description = 'Item Type'

    def sku_type_badge(self, obj):
        return format_html(
            '<span style="background-color: #6c757d; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            obj.get_sku_type_display()
        )
    sku_type_badge.short_description = 'SKU Type'

    def product_count(self, obj):
        count = obj.products.filter(is_active=True).count()
        url = reverse('admin:inventory_product_changelist') + f'?category__id__exact={obj.id}'
        return format_html('<a href="{}">{} products</a>', url, count)
    product_count.short_description = 'Products'

    def total_inventory_value(self, obj):
        total = sum(
            (Decimal(p.buying_price or 0) * Decimal(p.quantity or 0))
            for p in obj.products.filter(is_active=True)
        )
        # Format the number first, then pass as string to format_html
        formatted_value = '${:,.2f}'.format(float(total))
        return format_html('<strong>{}</strong>', formatted_value)
    total_inventory_value.short_description = 'Inventory Value'

    def created_info(self, obj):
        products = obj.products.filter(is_active=True)
        if getattr(obj, 'is_single_item', False):
            available = sum(1 for p in products if p.status == 'available')
            sold = sum(1 for p in products if p.status == 'sold')
            info = f"Available: {available} | Sold: {sold}"
        else:
            total_qty = sum(p.quantity or 0 for p in products)
            available = sum(1 for p in products if p.status == 'available')
            lowstock = sum(1 for p in products if p.status == 'lowstock')
            outofstock = sum(1 for p in products if p.status == 'outofstock')
            info = (
                f"Total Units: {total_qty} | "
                f"Available: {available} | "
                f"Low Stock: {lowstock} | "
                f"Out: {outofstock}"
            )
        return info
    created_info.short_description = 'Category Statistics'


# ============================================
# PRODUCT ADMIN
# ============================================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'product_code',
        'name',
        'category_link',
        'sku_value_short',
        'quantity_display',
        'status_badge',
        'pricing_info',
        'profit_display',
        'owner_link',
        'is_active',
    ]
    list_filter = [
        'is_active',
        'status',
        'category',
        'category__item_type',
        'created_at',
    ]
    search_fields = [
        'product_code',
        'name',
        'sku_value',
        'owner__username'
    ]
    readonly_fields = [
        'product_code',
        'status',
        'created_at',
        'updated_at',
        'inventory_summary',
        'profit_margin',
        'profit_percentage',
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'product_code',
                'name',
                'category',
                'sku_value',
            )
        }),
        ('Inventory', {
            'fields': (
                'quantity',
                'status',
            )
        }),
        ('Pricing', {
            'fields': (
                'buying_price',
                'selling_price',
                'profit_margin',
                'profit_percentage',
            )
        }),
        ('Ownership & Status', {
            'fields': (
                'owner',
                'is_active',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
        ('Summary', {
            'fields': ('inventory_summary',),
            'classes': ('collapse',)
        }),
    )

    inlines = [StockEntryInline]
    actions = [export_to_csv, mark_as_active, mark_as_inactive]
    date_hierarchy = 'created_at'
    list_per_page = 50

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('category', 'owner')

    def category_link(self, obj):
        if obj.category:
            url = reverse('admin:inventory_category_change', args=[obj.category.id])
            return format_html('<a href="{}">{}</a>', url, obj.category.name)
        return '-'
    category_link.short_description = 'Category'
    category_link.admin_order_field = 'category__name'

    def sku_value_short(self, obj):
        sku = obj.sku_value or ''
        return sku[:20] + '...' if len(sku) > 20 else sku
    sku_value_short.short_description = 'SKU'
    sku_value_short.admin_order_field = 'sku_value'

    def quantity_display(self, obj):
        # Defensive checks for None
        qty = obj.quantity or 0
        if getattr(obj.category, 'is_single_item', False):
            color = '#28a745' if qty > 0 else '#dc3545'
            text = 'Available' if qty > 0 else 'Sold'
        else:
            if qty > 5:
                color = '#28a745'
            elif qty > 0:
                color = '#ffc107'
            else:
                color = '#dc3545'
            text = str(qty)
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, text)
    quantity_display.short_description = 'Quantity'
    quantity_display.admin_order_field = 'quantity'

    def status_badge(self, obj):
        colors = {
            'available': '#28a745',
            'sold': '#6c757d',
            'lowstock': '#ffc107',
            'outofstock': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            (obj.get_status_display() or '').upper()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def pricing_info(self, obj):
        buy_price = float(Decimal(obj.buying_price or 0))
        sell_price = float(Decimal(obj.selling_price or 0))
        formatted_buy = '${:,.2f}'.format(buy_price)
        formatted_sell = '${:,.2f}'.format(sell_price)
        return format_html(
            'Buy: <strong>{}</strong><br>Sell: <strong>{}</strong>',
            formatted_buy,
            formatted_sell
        )
    pricing_info.short_description = 'Pricing'

    def profit_display(self, obj):
        margin = float(Decimal(obj.profit_margin or 0))
        percentage = float(Decimal(obj.profit_percentage or 0))
        color = '#28a745' if margin > 0 else '#dc3545'
        formatted_margin = '${:,.2f}'.format(margin)
        formatted_percentage = '{:.1f}%'.format(percentage)
        return format_html('<span style="color: {};">{} ({})</span>', color, formatted_margin, formatted_percentage)
    profit_display.short_description = 'Profit'

    def owner_link(self, obj):
        if obj.owner:
            url = reverse('admin:auth_user_change', args=[obj.owner.id])
            return format_html('<a href="{}">{}</a>', url, obj.owner.username)
        return '-'
    owner_link.short_description = 'Owner'
    owner_link.admin_order_field = 'owner__username'

    def inventory_summary(self, obj):
        # Aggregate stock entries
        stock_entries = obj.stock_entries.all()
        total_entries = stock_entries.count()
        purchases = stock_entries.filter(entry_type='purchase').aggregate(total=Sum('quantity'))['total'] or 0
        sales = stock_entries.filter(entry_type='sale').aggregate(total=Sum('quantity'))['total'] or 0
        returns = stock_entries.filter(entry_type='return').aggregate(total=Sum('quantity'))['total'] or 0
        adjustments = stock_entries.filter(entry_type='adjustment').aggregate(total=Sum('quantity'))['total'] or 0

        total_value = float(Decimal(obj.buying_price or 0) * Decimal(obj.quantity or 0))
        formatted_value = '${:,.2f}'.format(total_value)

        return format_html(
            """
            <table style="width:100%; border-collapse: collapse;">
                <tr style="background-color:#f8f9fa;">
                    <th style="padding:8px; text-align:left; border:1px solid #dee2e6;">Metric</th>
                    <th style="padding:8px; text-align:right; border:1px solid #dee2e6;">Value</th>
                </tr>
                <tr>
                    <td style="padding:8px; border:1px solid #dee2e6;">Total Stock Entries</td>
                    <td style="padding:8px; text-align:right; border:1px solid #dee2e6;">{}</td>
                </tr>
                <tr>
                    <td style="padding:8px; border:1px solid #dee2e6;">Total Purchased</td>
                    <td style="padding:8px; text-align:right; border:1px solid #dee2e6;">{} units</td>
                </tr>
                <tr>
                    <td style="padding:8px; border:1px solid #dee2e6;">Total Sold</td>
                    <td style="padding:8px; text-align:right; border:1px solid #dee2e6;">{} units</td>
                </tr>
                <tr>
                    <td style="padding:8px; border:1px solid #dee2e6;">Total Returns</td>
                    <td style="padding:8px; text-align:right; border:1px solid #dee2e6;">{} units</td>
                </tr>
                <tr>
                    <td style="padding:8px; border:1px solid #dee2e6;">Total Adjustments</td>
                    <td style="padding:8px; text-align:right; border:1px solid #dee2e6;">{} units</td>
                </tr>
                <tr style="background-color:#f8f9fa; font-weight:bold;">
                    <td style="padding:8px; border:1px solid #dee2e6;">Current Stock Value</td>
                    <td style="padding:8px; text-align:right; border:1px solid #dee2e6;">{}</td>
                </tr>
                <tr style="background-color:#f8f9fa; font-weight:bold;">
                    <td style="padding:8px; border:1px solid #dee2e6;">Can Restock</td>
                    <td style="padding:8px; text-align:right; border:1px solid #dee2e6;">{}</td>
                </tr>
            </table>
            """,
            total_entries,
            purchases,
            abs(sales),
            returns,
            adjustments,
            formatted_value,
            'Yes' if getattr(obj, 'can_restock', False) else 'No'
        )
    inventory_summary.short_description = 'Inventory Summary'


# ============================================
# STOCK ENTRY ADMIN
# ============================================

@admin.register(StockEntry)
class StockEntryAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'product_link',
        'entry_type_badge',
        'quantity_display',
        'unit_price',
        'total_amount_display',
        'reference_id',
        'created_by_link',
        'created_at',
    ]
    list_filter = [
        'entry_type',
        'created_at',
        'product__category',
    ]
    search_fields = [
        'product__product_code',
        'product__name',
        'reference_id',
        'notes',
        'created_by__username',
    ]
    readonly_fields = [
        'product',
        'quantity',
        'entry_type',
        'unit_price',
        'total_amount',
        'reference_id',
        'notes',
        'created_by',
        'created_at',
        'entry_summary',
    ]
    fieldsets = (
        ('Entry Information', {'fields': ('product', 'entry_type', 'quantity')}),
        ('Financial', {'fields': ('unit_price', 'total_amount')}),
        ('Reference', {'fields': ('reference_id', 'notes')}),
        ('Metadata', {'fields': ('created_by', 'created_at')}),
        ('Summary', {'fields': ('entry_summary',), 'classes': ('collapse',)}),
    )
    date_hierarchy = 'created_at'
    list_per_page = 100
    actions = [export_to_csv]

    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('product', 'product__category', 'created_by')

    def product_link(self, obj):
        if obj.product:
            url = reverse('admin:inventory_product_change', args=[obj.product.id])
            return format_html('<a href="{}">{} ({})</a>', url, obj.product.name, obj.product.product_code)
        return '-'
    product_link.short_description = 'Product'
    product_link.admin_order_field = 'product__name'

    def entry_type_badge(self, obj):
        colors = {
            'purchase': '#28a745',
            'sale': '#dc3545',
            'return': '#17a2b8',
            'adjustment': '#ffc107',
        }
        color = colors.get(obj.entry_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            (obj.get_entry_type_display() or '').upper()
        )
    entry_type_badge.short_description = 'Type'
    entry_type_badge.admin_order_field = 'entry_type'

    def quantity_display(self, obj):
        qty = obj.quantity or 0
        color = '#28a745' if getattr(obj, 'is_stock_in', False) else '#dc3545'
        sign = '+' if getattr(obj, 'is_stock_in', False) else ''
        return format_html('<span style="color: {}; font-weight: bold;">{}{}</span>', color, sign, qty)
    quantity_display.short_description = 'Quantity'
    quantity_display.admin_order_field = 'quantity'

    def total_amount_display(self, obj):
        total_amount = float(Decimal(obj.total_amount or 0))
        formatted_amount = '${:,.2f}'.format(total_amount)
        return format_html('<strong>{}</strong>', formatted_amount)
    total_amount_display.short_description = 'Total'
    total_amount_display.admin_order_field = 'total_amount'

    def created_by_link(self, obj):
        if obj.created_by:
            url = reverse('admin:auth_user_change', args=[obj.created_by.id])
            return format_html('<a href="{}">{}</a>', url, obj.created_by.username)
        return '-'
    created_by_link.short_description = 'Created By'
    created_by_link.admin_order_field = 'created_by__username'

    def entry_summary(self, obj):
        unit_price = float(Decimal(obj.unit_price or 0))
        total_amount = float(Decimal(obj.total_amount or 0))
        formatted_unit = '${:,.2f}'.format(unit_price)
        formatted_total = '${:,.2f}'.format(total_amount)
        
        return format_html(
            """
            <table style="width:100%; border-collapse: collapse;">
                <tr style="background-color:#f8f9fa;">
                    <th style="padding:8px; text-align:left; border:1px solid #dee2e6;">Detail</th>
                    <th style="padding:8px; text-align:right; border:1px solid #dee2e6;">Value</th>
                </tr>
                <tr>
                    <td style="padding:8px; border:1px solid #dee2e6;">Product</td>
                    <td style="padding:8px; text-align:right; border:1px solid #dee2e6;">{}</td>
                </tr>
                <tr>
                    <td style="padding:8px; border:1px solid #dee2e6;">Product Code</td>
                    <td style="padding:8px; text-align:right; border:1px solid #dee2e6;">{}</td>
                </tr>
                <tr>
                    <td style="padding:8px; border:1px solid #dee2e6;">Entry Type</td>
                    <td style="padding:8px; text-align:right; border:1px solid #dee2e6;">{}</td>
                </tr>
                <tr>
                    <td style="padding:8px; border:1px solid #dee2e6;">Quantity Change</td>
                    <td style="padding:8px; text-align:right; border:1px solid #dee2e6;">{}{}</td>
                </tr>
                <tr>
                    <td style="padding:8px; border:1px solid #dee2e6;">Unit Price</td>
                    <td style="padding:8px; text-align:right; border:1px solid #dee2e6;">{}</td>
                </tr>
                <tr style="background-color:#f8f9fa; font-weight:bold;">
                    <td style="padding:8px; border:1px solid #dee2e6;">Total Amount</td>
                    <td style="padding:8px; text-align:right; border:1px solid #dee2e6;">{}</td>
                </tr>
                <tr>
                    <td style="padding:8px; border:1px solid #dee2e6;">Reference ID</td>
                    <td style="padding:8px; text-align:right; border:1px solid #dee2e6;">{}</td>
                </tr>
                <tr>
                    <td style="padding:8px; border:1px solid #dee2e6;">Created By</td>
                    <td style="padding:8px; text-align:right; border:1px solid #dee2e6;">{}</td>
                </tr>
                <tr>
                    <td style="padding:8px; border:1px solid #dee2e6;">Created At</td>
                    <td style="padding:8px; text-align:right; border:1px solid #dee2e6;">{}</td>
                </tr>
                <tr>
                    <td colspan="2" style="padding:8px; border:1px solid #dee2e6;"><strong>Notes:</strong><br>{}</td>
                </tr>
            </table>
            """,
            obj.product.name if obj.product else '-',
            obj.product.product_code if obj.product else '-',
            obj.get_entry_type_display() if hasattr(obj, 'get_entry_type_display') else obj.entry_type,
            '+' if getattr(obj, 'is_stock_in', False) else '',
            obj.quantity or 0,
            formatted_unit,
            formatted_total,
            obj.reference_id or '-',
            (obj.created_by.username if obj.created_by else '-'),
            (obj.created_at.strftime('%Y-%m-%d %H:%M:%S') if getattr(obj, 'created_at', None) else '-'),
            obj.notes or '-'
        )
    entry_summary.short_description = 'Entry Details'


# ============================================
# ADMIN SITE CUSTOMIZATION
# ============================================

admin.site.site_header = "Inventory Management System"
admin.site.site_title = "Inventory Admin"
admin.site.index_title = "Welcome to Inventory Management"