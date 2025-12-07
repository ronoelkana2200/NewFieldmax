# sales/forms.py - FIXED VERSION

from django import forms
from .models import Sale, SaleItem


class SaleForm(forms.ModelForm):
    """
    Form for Sale model (transaction-level, not item-level)
    ✅ FIXED: Only includes fields that exist on Sale model
    """
    
    class Meta:
        model = Sale
        fields = [
            'buyer_name',
            'buyer_phone',
            'buyer_id_number',
            'nok_name',
            'nok_phone',
        ]
        widgets = {
            'buyer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Customer name'
            }),
            'buyer_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0712345678'
            }),
            'buyer_id_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ID number'
            }),
            'nok_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Next of kin name'
            }),
            'nok_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Next of kin phone'
            }),
        }


class SaleItemForm(forms.ModelForm):
    """
    Form for individual sale items
    Use this when adding items to a sale
    """
    
    class Meta:
        model = SaleItem
        fields = [
            'product',
            'quantity',
            'unit_price',
        ]
        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-control'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'value': 1
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': 0
            }),
        }


# ============================================
# FORMSETS FOR INLINE ITEM EDITING
# ============================================

from django.forms import inlineformset_factory

# Create formset for adding multiple items to a sale
SaleItemFormSet = inlineformset_factory(
    Sale,  # Parent model
    SaleItem,  # Child model
    form=SaleItemForm,
    extra=1,  # Number of empty forms to display
    can_delete=True,
    min_num=1,  # At least one item required
    validate_min=True
)


# ============================================
# ALTERNATIVE: Simple form for quick sale entry
# ============================================

class QuickSaleForm(forms.Form):
    """
    Simplified form for quick single-item sales
    Used in POS-style interfaces
    """
    
    product_code = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Scan or enter product code',
            'autofocus': True
        }),
        label='Product Code / SKU / IMEI'
    )
    
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1
        }),
        label='Quantity'
    )
    
    unit_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Auto-filled from product'
        }),
        label='Unit Price (Optional)'
    )
    
    # Client details (optional)
    buyer_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Customer name'
        }),
        label='Customer Name'
    )
    
    buyer_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0712345678'
        }),
        label='Phone Number'
    )
    
    buyer_id_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ID number'
        }),
        label='ID Number'
    )
    
    nok_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Next of kin name'
        }),
        label='Next of Kin'
    )
    
    nok_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Next of kin phone'
        }),
        label='Next of Kin Phone'
    )


# ============================================
# USAGE EXAMPLES
# ============================================
"""
# 1. CREATE SALE WITH FORMSET (Admin/Staff Interface)
# ===================================================

# In your view:
def create_sale_with_items(request):
    if request.method == 'POST':
        sale_form = SaleForm(request.POST)
        item_formset = SaleItemFormSet(request.POST)
        
        if sale_form.is_valid() and item_formset.is_valid():
            sale = sale_form.save(commit=False)
            sale.seller = request.user
            sale.save()
            
            items = item_formset.save(commit=False)
            for item in items:
                item.sale = sale
                item.save()
                item.process_sale()  # Deduct stock
            
            sale.assign_etr_receipt_number()
            return redirect('sale-detail', sale_id=sale.sale_id)
    else:
        sale_form = SaleForm()
        item_formset = SaleItemFormSet()
    
    return render(request, 'sales/create_sale.html', {
        'sale_form': sale_form,
        'item_formset': item_formset
    })


# In your template:
<form method="post">
    {% csrf_token %}
    {{ sale_form.as_p }}
    
    <h3>Items</h3>
    {{ item_formset.management_form }}
    {% for form in item_formset %}
        {{ form.as_p }}
    {% endfor %}
    
    <button type="submit">Create Sale</button>
</form>


# 2. QUICK SALE FORM (POS Interface)
# ==================================

# In your view:
def quick_sale(request):
    if request.method == 'POST':
        form = QuickSaleForm(request.POST)
        
        if form.is_valid():
            # Process the sale (similar to your current BatchSaleCreateView)
            # ... your existing logic
            pass
    else:
        form = QuickSaleForm()
    
    return render(request, 'sales/quick_sale.html', {'form': form})


# 3. AJAX-BASED CART SYSTEM (Your Current Setup)
# ==============================================
# Continue using your current JavaScript cart system
# Just update the backend to create Sale + SaleItem records
# (as shown in the BatchSaleCreateView artifact)
"""


# ============================================
# ADMIN FORMS (Optional)
# ============================================

class SaleAdminForm(forms.ModelForm):
    """
    Form for Django admin
    Includes all fields including read-only ones
    """
    
    class Meta:
        model = Sale
        fields = '__all__'
        widgets = {
            'sale_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local'
            }),
        }


class SaleItemInlineForm(forms.ModelForm):
    """
    Inline form for editing sale items in admin
    """
    
    class Meta:
        model = SaleItem
        fields = [
            'product',
            'product_code',
            'product_name',
            'sku_value',
            'quantity',
            'unit_price',
            'total_price',
        ]
        widgets = {
            'product_code': forms.TextInput(attrs={'readonly': True}),
            'product_name': forms.TextInput(attrs={'readonly': True}),
            'sku_value': forms.TextInput(attrs={'readonly': True}),
            'total_price': forms.NumberInput(attrs={'readonly': True}),
        }