from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.views.decorators.http import require_http_methods
from django.db import transaction
from rest_framework import viewsets
import json
from decimal import Decimal, InvalidOperation
import traceback
from django.core.exceptions import ValidationError
from django.contrib import messages
from .models import Category, Product, StockEntry
from .serializers import CategorySerializer, ProductSerializer, StockEntrySerializer
from .forms import CategoryForm, ProductForm, StockEntryForm
import logging


logger = logging.getLogger(__name__)

# ====================================
# REST API VIEWSETS
# ====================================

class CategoryViewSet(viewsets.ModelViewSet):
    """API endpoint for categories"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ProductViewSet(viewsets.ModelViewSet):
    """API endpoint for products"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    
    def get_queryset(self):
        """Filter products based on query parameters"""
        queryset = Product.objects.select_related('category', 'owner').all()
        
        # Filter by category
        category_id = self.request.query_params.get('category', None)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by status
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by item type (single/bulk)
        item_type = self.request.query_params.get('item_type', None)
        if item_type:
            queryset = queryset.filter(category__item_type=item_type)
        
        # Search by name or SKU
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(sku_value__icontains=search) |
                Q(product_code__icontains=search)
            )
        
        return queryset


class StockEntryViewSet(viewsets.ModelViewSet):
    """API endpoint for stock entries"""
    queryset = StockEntry.objects.all()
    serializer_class = StockEntrySerializer
    
    def get_queryset(self):
        """Filter stock entries by product or date range"""
        queryset = StockEntry.objects.select_related('product', 'created_by').all()
        
        # Filter by product
        product_id = self.request.query_params.get('product', None)
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        # Filter by entry type
        entry_type = self.request.query_params.get('entry_type', None)
        if entry_type:
            queryset = queryset.filter(entry_type=entry_type)
        
        return queryset


# ====================================
# CATEGORY VIEWS
# ====================================

class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = "inventory/category_list.html"
    context_object_name = "categories"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add product counts per category
        for category in context['categories']:
            category.product_count = category.products.filter(is_active=True).count()
        return context


class CategoryDetailView(LoginRequiredMixin, DetailView):
    model = Category
    template_name = "inventory/category_detail.html"
    context_object_name = "category"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.get_object()
        
        # Get products in this category
        context['products'] = category.products.filter(is_active=True)
        context['total_products'] = context['products'].count()
        
        # Calculate inventory value safely
        total_value = Decimal('0.00')
        for p in context['products']:
            buying_price = p.buying_price or Decimal('0.00')
            quantity = p.quantity or 0
            total_value += buying_price * quantity
        
        context['inventory_value'] = total_value
        
        return context

# inventory/views.py
from django.views.generic import CreateView
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import redirect, render
from .models import Category
from .forms import CategoryForm, ProductFormSet

class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "inventory/category_form.html"
    success_url = reverse_lazy("inventory:category-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['item_type_choices'] = Category.ITEM_TYPE_CHOICES
        context['sku_type_choices'] = Category.SKU_TYPE_CHOICES
        return context

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['products'] = ProductFormSet(self.request.POST)
        else:
            data['products'] = ProductFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        products = context['products']
        if products.is_valid():
            self.object = form.save()
            products.instance = self.object
            products.save()
            
            # AJAX response
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': f'Category "{self.object.name}" created successfully',
                    'category_id': self.object.pk
                })
            
            return super().form_valid(form)
        else:
            return self.form_invalid(form)



class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "inventory/category_form.html"
    success_url = reverse_lazy("category-list")


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = "inventory/category_confirm_delete.html"
    success_url = reverse_lazy("category-list")
    
    def post(self, request, *args, **kwargs):
        category = self.get_object()
        
        # Check if category has products
        if category.products.exists():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': f'Cannot delete category. It has {category.products.count()} products.'
                }, status=400)
        
        return super().post(request, *args, **kwargs)


# ====================================
# PRODUCT VIEWS
# ====================================

class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "inventory/product_list.html"
    context_object_name = "products"
    paginate_by = 50
    
    def get_queryset(self):
        queryset = Product.objects.select_related('category', 'owner').filter(is_active=True)
        
        # Filter by category
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(product_code__icontains=search) |
                Q(sku_value__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['total_products'] = self.get_queryset().count()
        return context


class ProductDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        try:
            product = get_object_or_404(
                Product.objects.select_related('category', 'owner'),
                pk=pk
            )

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Safely handle None values
                buying_price = float(product.buying_price or 0)
                selling_price = float(product.selling_price or 0)
                profit_margin = float(product.profit_margin or 0)
                profit_percentage = float(product.profit_percentage or 0)

                owner_data = None
                if product.owner:
                    owner_data = {
                        'id': product.owner.id,
                        'username': product.owner.username
                    }

                return JsonResponse({
                    'status': 'success',
                    'product': {
                        'id': product.id,
                        'product_code': product.product_code,
                        'name': product.name,
                        'category': {
                            'id': product.category.id,
                            'name': product.category.name,
                            'item_type': product.category.item_type,
                            'sku_type': product.category.get_sku_type_display(),
                        },
                        'sku_value': product.sku_value,
                        'quantity': product.quantity or 0,
                        'buying_price': buying_price,
                        'selling_price': selling_price,
                        'status': product.get_status_display(),
                        'can_restock': getattr(product, 'can_restock', False),
                        'profit_margin': profit_margin,
                        'profit_percentage': profit_percentage,
                        'is_active': product.is_active,
                        'owner': owner_data,
                        'created_at': product.created_at.isoformat() if product.created_at else None,
                    }
                })

            # Normal HTML request
            context = {
                'product': product,
                'stock_entries': product.stock_entries.all()[:20],
                'total_stock_entries': product.stock_entries.count(),
            }
            return render(request, 'inventory/product_detail.html', context)

        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=400)
            raise






class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "inventory/product_form.html"
    success_url = reverse_lazy("inventory:product-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Product'
        context['button_text'] = 'Create Product'
        context['categories'] = Category.objects.all()
        return context

    def post(self, request, *args, **kwargs):
        """Handle AJAX & normal POST"""
        self.object = None
        
        logger.info("=== ProductCreateView POST ===")
        logger.info(f"POST data: {request.POST}")
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        logger.info(f"Is AJAX: {is_ajax}")
        
        try:
            form = self.get_form()
            logger.info("Form created successfully")

            if form.is_valid():
                logger.info("Form is valid")
                return self.form_valid(form)
            else:
                logger.error(f"Form invalid: {form.errors}")
                return self.form_invalid(form)

        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"ERROR in POST: {str(e)}")
            logger.error(traceback.format_exc())
            logger.error("=" * 80)
            if is_ajax:
                return JsonResponse({'success': False, 'message': str(e)}, status=500)
            raise

    def form_valid(self, form):
        logger.info("=== form_valid START ===")
        try:
            with transaction.atomic():
                category = form.cleaned_data.get('category')
                name = form.cleaned_data.get('name')
                sku_value = (form.cleaned_data.get('sku_value') or "").strip()
                quantity = form.cleaned_data.get('quantity') or 1
                buying_price = form.cleaned_data.get('buying_price')
                selling_price = form.cleaned_data.get('selling_price')

                # ===============================
                # SINGLE ITEM
                # ===============================
                if category.is_single_item:
                    if not sku_value:
                        raise ValidationError(f"{category.get_sku_type_display()} is required for single items")
                    if Product.objects.filter(sku_value__iexact=sku_value, is_active=True).exists():
                        raise ValidationError(f"{category.get_sku_type_display()} '{sku_value}' already exists")
                    
                    form.instance.owner = self.request.user
                    form.instance.quantity = 1
                    self.object = form.save()
                    
                    # Create stock entry
                    StockEntry.objects.create(
                        product=self.object,
                        quantity=1,
                        entry_type='purchase',
                        unit_price=buying_price,
                        total_amount=buying_price,
                        created_by=self.request.user,
                        notes="Initial single item stock entry"
                    )
                    logger.info(f"[SINGLE ITEM] Product created: {self.object.product_code}")

                # ===============================
                # BULK ITEM
                # ===============================
                else:
                    existing_product = Product.objects.filter(
                        name__iexact=name,
                        category=category,
                        is_active=True
                    ).first()
                    
                    if existing_product:
                        self.object = existing_product
                        logger.info(f"[BULK ITEM] Found existing product: {existing_product.product_code}")
                    else:
                        # Create new product with quantity=0
                        form.instance.owner = self.request.user
                        form.instance.quantity = 0
                        self.object = form.save()
                        logger.info(f"[BULK ITEM] Created new product: {self.object.product_code}")

                    # Create stock entry to add quantity
                    StockEntry.objects.create(
                        product=self.object,
                        quantity=quantity,
                        entry_type='purchase',
                        unit_price=buying_price,
                        total_amount=buying_price * quantity,
                        created_by=self.request.user,
                        notes="Initial stock entry via ProductCreateView"
                    )
                    logger.info(f"[BULK ITEM] Stock entry created for {self.object.product_code}, Qty: {quantity}")

                # Return response
                if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        "success": True,
                        "message": f'Product "{self.object.name}" saved successfully!',
                        "product_id": self.object.pk,
                        "product_code": self.object.product_code,
                        "quantity": self.object.quantity
                    })
                else:
                    return redirect(self.success_url)

        except ValidationError as ve:
            logger.error(f"ValidationError: {ve}")
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': str(ve)}, status=400)
            form.add_error(None, str(ve))
            return self.form_invalid(form)

        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"ERROR: {str(e)}")
            logger.error(traceback.format_exc())
            logger.error("=" * 80)
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': f'Server error: {str(e)}'}, status=500)
            form.add_error(None, str(e))
            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.error(f"Form invalid - Errors: {form.errors}")
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            error_message = "Validation error"
            if form.errors:
                for field, errors in form.errors.items():
                    if errors:
                        error_message = f"{field}: {errors[0]}" if field != '__all__' else errors[0]
                        break
            return JsonResponse({
                "success": False,
                "message": error_message,
                "errors": dict(form.errors)
            }, status=400)
        return super().form_invalid(form)

    






# views.py

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
import logging
import traceback
import json

logger = logging.getLogger(__name__)


class ProductRestockView(LoginRequiredMixin, TemplateView):
    """View for restocking products - search first, then restock"""
    template_name = "inventory/product_restock.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Restock Products'
        return context


@login_required
@require_http_methods(["GET"])
def search_product_for_restock(request):
    """Search for a product by name, code, or SKU"""
    search_term = request.GET.get('search', '').strip()
    
    if not search_term:
        return JsonResponse({
            'success': False,
            'message': 'Please enter a product name, code, or SKU'
        }, status=400)
    
    try:
        # Search in multiple fields
        products = Product.objects.filter(
            Q(name__icontains=search_term) |
            Q(product_code__icontains=search_term) |
            Q(sku_value__iexact=search_term),
            is_active=True
        ).select_related('category')
        
        if not products.exists():
            return JsonResponse({
                'success': False,
                'message': f'No product found matching "{search_term}"'
            }, status=404)
        
        # If multiple products found, return list
        if products.count() > 1:
            product_list = [{
                'id': p.id,
                'name': p.name,
                'product_code': p.product_code,
                'sku_value': p.sku_value or 'N/A',
                'category': p.category.name,
                'current_quantity': p.quantity,
                'buying_price': float(p.buying_price) if p.buying_price else 0,
                'selling_price': float(p.selling_price) if p.selling_price else 0,
                'is_single_item': p.category.is_single_item
            } for p in products[:10]]  # Limit to 10 results
            
            return JsonResponse({
                'success': True,
                'multiple': True,
                'products': product_list,
                'count': products.count()
            })
        
        # Single product found
        product = products.first()
        
        # Check if it's a single item
        if product.category.is_single_item:
            return JsonResponse({
                'success': False,
                'message': f'"{product.name}" is a single item and cannot be restocked. Each single item must be added individually.',
                'is_single_item': True
            }, status=400)
        
        return JsonResponse({
            'success': True,
            'multiple': False,
            'product': {
                'id': product.id,
                'name': product.name,
                'product_code': product.product_code,
                'sku_value': product.sku_value or 'N/A',
                'category': product.category.name,
                'current_quantity': product.quantity,
                'buying_price': float(product.buying_price) if product.buying_price else 0,
                'selling_price': float(product.selling_price) if product.selling_price else 0,
                'is_single_item': product.category.is_single_item
            }
        })
    
    except Exception as e:
        logger.error(f"Search error: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'message': f'Search error: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def process_restock(request):
    """Process the restock operation"""
    try:
        product_id = request.POST.get('product_id')
        quantity = request.POST.get('quantity')
        buying_price = request.POST.get('buying_price')
        selling_price = request.POST.get('selling_price')
        notes = request.POST.get('notes', '').strip()
        
        # Validation
        if not all([product_id, quantity, buying_price]):
            return JsonResponse({
                'success': False,
                'message': 'Product, quantity, and buying price are required'
            }, status=400)
        
        product = get_object_or_404(Product, pk=product_id, is_active=True)
        
        # Check if single item
        if product.category.is_single_item:
            return JsonResponse({
                'success': False,
                'message': 'Cannot restock single items'
            }, status=400)
        
        try:
            quantity = int(quantity)
            buying_price = float(buying_price)
            selling_price = float(selling_price) if selling_price else None
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid number format'
            }, status=400)
        
        if quantity <= 0:
            return JsonResponse({
                'success': False,
                'message': 'Quantity must be greater than 0'
            }, status=400)
        
        if buying_price < 0:
            return JsonResponse({
                'success': False,
                'message': 'Buying price cannot be negative'
            }, status=400)
        
        # Create stock entry and update prices
        with transaction.atomic():
            # Create stock entry
            stock_entry = StockEntry.objects.create(
                product=product,
                quantity=quantity,
                entry_type='purchase',
                unit_price=buying_price,
                total_amount=buying_price * quantity,
                created_by=request.user,
                notes=notes or "Restock via search"
            )
            
            # Update product prices if provided
            if buying_price:
                product.buying_price = buying_price
            if selling_price and selling_price > 0:
                product.selling_price = selling_price
            product.save()
            
            logger.info(f"Restocked: {product.product_code} - Qty: {quantity}")
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully added {quantity} units to {product.name}',
            'product': {
                'id': product.id,
                'name': product.name,
                'product_code': product.product_code,
                'new_quantity': product.quantity,
                'buying_price': float(product.buying_price),
                'selling_price': float(product.selling_price)
            },
            'stock_entry_id': stock_entry.id
        })
    
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Product not found'
        }, status=404)
    
    except Exception as e:
        logger.error(f"Restock error: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=500)






class ProductEditView(LoginRequiredMixin, UpdateView):
    """Handle product editing"""
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('product-list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Product'
        context['button_text'] = 'Update Product'
        context['categories'] = Category.objects.all()
        return context
    
    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Track quantity changes
                old_product = Product.objects.get(pk=self.object.pk)
                old_quantity = old_product.quantity or 0
                new_quantity = form.cleaned_data.get('quantity', 0) or 0
                
                response = super().form_valid(form)
                
                # Create adjustment entry if quantity changed
                if old_quantity != new_quantity:
                    quantity_diff = new_quantity - old_quantity
                    buying_price = self.object.buying_price or Decimal('0.00')
                    
                    StockEntry.objects.create(
                        product=self.object,
                        quantity=quantity_diff,
                        entry_type='adjustment',
                        unit_price=buying_price,
                        total_amount=abs(quantity_diff) * buying_price,
                        created_by=self.request.user,
                        notes=f"Manual adjustment: {old_quantity} → {new_quantity}"
                    )
                
                # AJAX response
                if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'message': f'Product "{self.object.name}" updated successfully',
                        'product_id': self.object.pk
                    })
                
                return response
            
        except Exception as e:
            print("Error updating product:")
            print(traceback.format_exc())
            
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': f'Error updating product: {str(e)}'
                }, status=400)
            raise
    
    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'Validation error',
                'errors': form.errors
            }, status=400)
        return super().form_invalid(form)


class ProductUpdateView(LoginRequiredMixin, View):
    """AJAX-only quick update for product fields"""
    
    def post(self, request, pk):
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                product = get_object_or_404(Product, pk=pk)
                
                # Track old values
                old_quantity = product.quantity or 0
                
                # Update fields
                if 'name' in data:
                    product.name = data['name']
                    
                if 'buying_price' in data and data['buying_price'] not in [None, '']:
                    try:
                        product.buying_price = Decimal(str(data['buying_price']))
                    except (ValueError, InvalidOperation):
                        return JsonResponse({
                            'status': 'error',
                            'message': 'Invalid buying price format'
                        }, status=400)
                
                if 'selling_price' in data and data['selling_price'] not in [None, '']:
                    try:
                        product.selling_price = Decimal(str(data['selling_price']))
                    except (ValueError, InvalidOperation):
                        return JsonResponse({
                            'status': 'error',
                            'message': 'Invalid selling price format'
                        }, status=400)
                
                if 'quantity' in data:
                    try:
                        new_quantity = int(data['quantity'])
                    except (ValueError, TypeError):
                        return JsonResponse({
                            'status': 'error',
                            'message': 'Invalid quantity format'
                        }, status=400)
                    
                    # Validate quantity change for single items
                    if hasattr(product.category, 'is_single_item') and product.category.is_single_item:
                        if new_quantity not in [0, 1]:
                            return JsonResponse({
                                'status': 'error',
                                'message': 'Single items can only have quantity 0 or 1'
                            }, status=400)
                    
                    product.quantity = new_quantity
                
                product.save()
                
                # Create adjustment entry if quantity changed
                if 'quantity' in data and old_quantity != product.quantity:
                    quantity_diff = product.quantity - old_quantity
                    buying_price = product.buying_price or Decimal('0.00')
                    
                    StockEntry.objects.create(
                        product=product,
                        quantity=quantity_diff,
                        entry_type='adjustment',
                        unit_price=buying_price,
                        total_amount=abs(quantity_diff) * buying_price,
                        created_by=request.user,
                        notes="Quick update adjustment"
                    )
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Product updated successfully'
                })
            
        except Exception as e:
            print("Error in quick update:")
            print(traceback.format_exc())
            return JsonResponse({
                'status': 'error',
                'message': f'Error: {str(e)}'
            }, status=400)


class ProductDeleteView(LoginRequiredMixin, View):
    """Handle AJAX product deletion"""
    
    def post(self, request, pk):
        try:
            product = get_object_or_404(Product, pk=pk)
            product_name = product.name
            product_code = product.product_code
            
            # Soft delete (mark as inactive) instead of hard delete
            product.is_active = False
            product.save()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Product "{product_name}" ({product_code}) deleted successfully'
            })
            
        except Product.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Product not found'
            }, status=404)
            
        except Exception as e:
            print("Error deleting product:")
            print(traceback.format_exc())
            return JsonResponse({
                'status': 'error',
                'message': f'Error deleting product: {str(e)}'
            }, status=400)


class ProductTransferView(LoginRequiredMixin, View):
    """Transfer product ownership to another user"""
    
    def post(self, request, pk):
        try:
            with transaction.atomic():
                product = get_object_or_404(Product, pk=pk)
                user_id = request.POST.get("user_id")
                qty = int(request.POST.get("quantity", 1))
                
                # Validate user
                try:
                    new_owner = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    return JsonResponse({
                        "status": "error",
                        "message": "Invalid user selected"
                    })
                
                # Validate quantity
                product_qty = product.quantity or 0
                if qty > product_qty:
                    return JsonResponse({
                        "status": "error",
                        "message": f"Not enough quantity available. Only {product_qty} in stock."
                    })
                
                # For single items, transfer the whole product
                if hasattr(product.category, 'is_single_item') and product.category.is_single_item:
                    product.owner = new_owner
                    product.save()
                    
                    # Create transfer record
                    StockEntry.objects.create(
                        product=product,
                        quantity=0,  # Transfer doesn't change quantity
                        entry_type='adjustment',
                        unit_price=product.buying_price or Decimal('0.00'),
                        total_amount=Decimal('0.00'),
                        created_by=request.user,
                        notes=f"Transferred ownership to {new_owner.username}"
                    )
                else:
                    # For bulk items
                    product.quantity = product_qty - qty
                    product.save()
                    
                    # Create new product for new owner
                    transferred_product = Product.objects.create(
                        name=product.name,
                        category=product.category,
                        sku_value=product.sku_value,
                        quantity=qty,
                        buying_price=product.buying_price,
                        selling_price=product.selling_price,
                        owner=new_owner
                    )
                    
                    # Record the transfer
                    buying_price = product.buying_price or Decimal('0.00')
                    StockEntry.objects.create(
                        product=product,
                        quantity=-qty,
                        entry_type='adjustment',
                        unit_price=buying_price,
                        total_amount=qty * buying_price,
                        created_by=request.user,
                        notes=f"Transferred {qty} units to {new_owner.username}"
                    )
                
                return JsonResponse({
                    "status": "success",
                    "message": f"Successfully transferred to {new_owner.username}"
                })
            
        except Exception as e:
            print("Error transferring product:")
            print(traceback.format_exc())
            return JsonResponse({
                "status": "error",
                "message": f'Error: {str(e)}'
            }, status=400)


class InventoryProductLookupView(LoginRequiredMixin, View):
    """
    Search for products by product_code or SKU value
    Used in POS/Sales systems
    """
    
    def get(self, request):
        search_term = request.GET.get("product_code", "").strip()
        
        if not search_term:
            return JsonResponse({
                "status": "error",
                "message": "Search term is required"
            })
        
        # Search by product_code or sku_value
        product = Product.objects.filter(
            Q(product_code__iexact=search_term) | Q(sku_value__iexact=search_term),
            is_active=True
        ).select_related('category').first()
        
        if not product:
            return JsonResponse({
                "status": "error",
                "message": "Product not found"
            })
        
        # Check if product is available
        if product.status in ['sold', 'outofstock']:
            return JsonResponse({
                "status": "error",
                "message": f"Product is {product.get_status_display()}"
            })
        
        return JsonResponse({
            "status": "success",
            "product_id": product.id,
            "product_name": product.name,
            "product_code": product.product_code,
            "sku_value": product.sku_value or "N/A",
            "sku_value": product.sku_value,
            "quantity": product.quantity or 0,
            "selling_price": str(product.selling_price or '0.00'),
            "buying_price": str(product.buying_price or '0.00'),
            "category": product.category.name,
            "item_type": product.category.item_type,
            "is_single_item": product.category.is_single_item,
            "category_code": product.category.category_code, 
            "created_at": product.created_at.isoformat(),
        })


# ====================================
# STOCK ENTRY VIEWS
# ====================================

class StockEntryListView(LoginRequiredMixin, ListView):
    model = StockEntry
    template_name = "inventory/stockentry_list.html"
    context_object_name = "entries"
    paginate_by = 50
    
    def get_queryset(self):
        queryset = StockEntry.objects.select_related(
            'product', 'product__category', 'created_by'
        ).all()
        
        # Filter by product
        product_id = self.request.GET.get('product')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        # Filter by entry type
        entry_type = self.request.GET.get('entry_type')
        if entry_type:
            queryset = queryset.filter(entry_type=entry_type)
        
        # Filter by date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.filter(is_active=True)
        context['entry_types'] = StockEntry.ENTRY_TYPE_CHOICES
        return context


class StockEntryCreateView(LoginRequiredMixin, CreateView):
    model = StockEntry
    form_class = StockEntryForm
    template_name = "inventory/stockentry_form.html"
    success_url = reverse_lazy("stockentry-list")
    
    def form_valid(self, form):
        try:
            # Set created_by
            form.instance.created_by = self.request.user
            
            response = super().form_valid(form)
            
            # AJAX response
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Stock entry created successfully',
                    'entry_id': self.object.pk
                })
            
            return response
            
        except Exception as e:
            print("Error creating stock entry:")
            print(traceback.format_exc())
            
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': f'Error: {str(e)}'
                }, status=400)
            raise


# ====================================
# UTILITY VIEWS
# ====================================

@login_required
def get_product_by_sku(request):
    """Get product info by SKU value (for barcode scanning)"""
    sku_value = request.GET.get('sku', '').strip()
    
    if not sku_value:
        return JsonResponse({'status': 'error', 'message': 'SKU required'})
    
    product = Product.objects.filter(
        sku_value=sku_value,
        is_active=True
    ).select_related('category').first()
    
    if not product:
        return JsonResponse({'status': 'error', 'message': 'Product not found'})
    
    return JsonResponse({
        'status': 'success',
        'product': {
            'id': product.id,
            'name': product.name,
            'product_code': product.product_code,
            'sku_value': product.sku_value,
            'quantity': product.quantity or 0,
            'selling_price': float(product.selling_price or 0),
            'status': product.status,
        }
    })


@login_required
def dashboard_stats(request):
    """Get inventory statistics for dashboard"""
    
    total_products = Product.objects.filter(is_active=True).count()
    
    # Single items stats
    single_items = Product.objects.filter(
        is_active=True,
        category__item_type='single'
    )
    single_available = single_items.filter(status='available').count()
    single_sold = single_items.filter(status='sold').count()
    
    # Bulk items stats
    bulk_items = Product.objects.filter(
        is_active=True,
        category__item_type='bulk'
    )
    bulk_available = bulk_items.filter(status='available').count()
    bulk_lowstock = bulk_items.filter(status='lowstock').count()
    bulk_outofstock = bulk_items.filter(status='outofstock').count()
    
    # Inventory value - calculate safely
    total_value = Decimal('0.00')
    for p in Product.objects.filter(is_active=True):
        buying_price = p.buying_price or Decimal('0.00')
        quantity = p.quantity or 0
        total_value += buying_price * quantity
    
    return JsonResponse({
        'total_products': total_products,
        'single_items': {
            'total': single_items.count(),
            'available': single_available,
            'sold': single_sold,
        },
        'bulk_items': {
            'total': bulk_items.count(),
            'available': bulk_available,
            'lowstock': bulk_lowstock,
            'outofstock': bulk_outofstock,
        },
        'inventory_value': float(total_value),
    })