# ====================================
#  IMPORTS
# ====================================
from django.shortcuts import render
from inventory.models import Category, Product








# ====================================
#  CATEG0RY
# ====================================
def categories(request):
    """Make categories available to all templates"""
    return {
        'categories': Category.objects.all().order_by('name')
    }



# ====================================
#  SHOP
# ====================================
def shop(request):
    # Get category filter from URL
    category_id = request.GET.get('category')
    
    # Filter products
    products = Product.objects.filter(is_active=True)
    
    if category_id:
        try:
            selected_category = Category.objects.get(id=category_id)
            products = products.filter(category=selected_category)
            categories_to_display = [selected_category]
        except Category.DoesNotExist:
            selected_category = None
            categories_to_display = Category.objects.all()
    else:
        selected_category = None
        categories_to_display = Category.objects.all()
    
    # Prepare categories with their products
    categories_with_products = []
    for category in categories_to_display:
        category.filtered_products = products.filter(category=category)
        if category.filtered_products.exists():
            categories_with_products.append(category)
    
    context = {
        'categories': categories_with_products,
        'selected_category': selected_category,
    }
    
    return render(request, 'website/shop.html', context)