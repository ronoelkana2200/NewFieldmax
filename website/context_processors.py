# website/context_processors.py
"""
Global context processors that make data available to all templates
"""
from inventory.models import Category
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)

def categories_processor(request):
    """
    Make categories available globally in all templates
    This runs for every request and adds categories to template context
    """
    try:
        # Get all active categories ordered by name
        categories = Category.objects.all().order_by('name')
        
        # Count products per category (only active products)
        categories_with_counts = []
        for category in categories:
            product_count = category.products.filter(is_active=True).count()
            
            categories_with_counts.append({
                'id': category.id,
                'name': category.name,
                'category_code': category.category_code,
                'item_type': category.item_type,
                'sku_type': category.sku_type,
                'is_single_item': category.is_single_item,
                'product_count': product_count,
                'url': f"{reverse('shop')}?category={category.id}"
            })
        
        return {
            'categories': categories_with_counts,
            'total_categories': len(categories_with_counts)
        }
    
    except Exception as e:
        logger.error(f"Error loading categories in context processor: {str(e)}")
        return {
            'categories': [],
            'total_categories': 0
        }


def dashboard_url(request):
    """
    Make dashboard URL available globally in all templates
    Returns appropriate dashboard based on user role
    """
    url = '#'
    
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile') and request.user.profile:
            role = request.user.profile.role
            if role == 'admin':
                url = '/admin-dashboard/'
            elif role == 'manager':
                url = '/manager-dashboard/'
            elif role == 'agent':
                url = '/agent-dashboard/'
            elif role == 'cashier':
                url = '/cashier-dashboard/'
        elif request.user.is_superuser:
            url = '/admin-dashboard/'
    
    return {'dashboard_url': url}


def cart_data(request):
    """
    Make cart information available globally
    Used for cart badge count in navigation
    """
    # For authenticated users (staff), don't show cart
    if request.user.is_authenticated:
        return {'cart_count': 0}
    
    # For guests, cart is in localStorage (handled by JavaScript)
    # This is just a placeholder for server-side rendering
    return {'cart_count': 0}