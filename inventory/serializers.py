from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Category, Product, StockEntry


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model"""
    
    item_type_display = serializers.CharField(source='get_item_type_display', read_only=True)
    sku_type_display = serializers.CharField(source='get_sku_type_display', read_only=True)
    product_count = serializers.SerializerMethodField()
    is_single_item = serializers.BooleanField(read_only=True)
    is_bulk_item = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Category
        fields = [
            'id',
            'name',
            'item_type',
            'item_type_display',
            'sku_type',
            'sku_type_display',
            'category_code',
            'is_single_item',
            'is_bulk_item',
            'product_count',
        ]
        read_only_fields = ['id', 'category_code']
    
    def get_product_count(self, obj):
        """Count active products in this category"""
        return obj.products.filter(is_active=True).count()
    
    def validate(self, data):
        """Validate category data"""
        # Ensure sku_type is provided
        if not data.get('sku_type'):
            raise serializers.ValidationError({
                'sku_type': 'SKU type is required for all categories'
            })
        
        return data


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product lists"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_item_type = serializers.CharField(source='category.item_type', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    can_restock = serializers.BooleanField(read_only=True)
    profit_margin = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        read_only=True
    )
    
    class Meta:
        model = Product
        fields = [
            'id',
            'product_code',
            'name',
            'category',
            'category_name',
            'category_item_type',
            'sku_value',
            'quantity',
            'buying_price',
            'selling_price',
            'status',
            'status_display',
            'can_restock',
            'profit_margin',
            'owner',
            'owner_username',
            'is_active',
            'created_at',
        ]
        read_only_fields = ['id', 'product_code', 'status', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    """Full serializer for product details"""
    
    category_detail = CategorySerializer(source='category', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    owner_detail = UserSerializer(source='owner', read_only=True)
    can_restock = serializers.BooleanField(read_only=True)
    profit_margin = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        read_only=True
    )
    profit_percentage = serializers.FloatField(read_only=True)
    total_value = serializers.SerializerMethodField()
    stock_entry_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id',
            'product_code',
            'name',
            'category',
            'category_detail',
            'sku_value',
            'quantity',
            'buying_price',
            'selling_price',
            'status',
            'status_display',
            'can_restock',
            'profit_margin',
            'profit_percentage',
            'total_value',
            'owner',
            'owner_detail',
            'is_active',
            'created_at',
            'updated_at',
            'stock_entry_count',
        ]
        read_only_fields = [
            'id', 
            'product_code', 
            'status', 
            'created_at', 
            'updated_at'
        ]
    
    def get_total_value(self, obj):
        """Calculate total inventory value for this product"""
        return float(obj.buying_price * obj.quantity)
    
    def get_stock_entry_count(self, obj):
        """Count stock entries for this product"""
        return obj.stock_entries.count()
    
    def validate(self, data):
        """Validate product data"""
        category = data.get('category')
        quantity = data.get('quantity', 1)
        buying_price = data.get('buying_price')
        selling_price = data.get('selling_price')
        
        # Validate pricing
        if buying_price and selling_price:
            if buying_price > selling_price:
                raise serializers.ValidationError({
                    'selling_price': 'Selling price must be greater than buying price'
                })
        
        # Validate single item quantity
        if category and category.is_single_item:
            if quantity not in [0, 1]:
                raise serializers.ValidationError({
                    'quantity': 'Single items must have quantity of 0 or 1'
                })
        
        # Validate bulk item quantity
        if category and category.is_bulk_item:
            if quantity < 0:
                raise serializers.ValidationError({
                    'quantity': 'Quantity cannot be negative'
                })
        
        return data
    
    def create(self, validated_data):
        """Create product and initial stock entry"""
        # Extract quantity for stock entry
        quantity = validated_data.get('quantity', 1)
        
        # Create product
        product = super().create(validated_data)
        
        # Create initial stock entry if quantity > 0
        if quantity > 0:
            StockEntry.objects.create(
                product=product,
                quantity=quantity,
                entry_type='purchase',
                unit_price=product.buying_price,
                total_amount=product.buying_price * quantity,
                created_by=self.context['request'].user if 'request' in self.context else None,
                notes="Initial stock entry via API"
            )
        
        return product
    
    def update(self, instance, validated_data):
        """Update product and create adjustment entry if quantity changed"""
        old_quantity = instance.quantity
        new_quantity = validated_data.get('quantity', old_quantity)
        
        # Update product
        product = super().update(instance, validated_data)
        
        # Create adjustment entry if quantity changed
        if old_quantity != new_quantity:
            quantity_diff = new_quantity - old_quantity
            StockEntry.objects.create(
                product=product,
                quantity=quantity_diff,
                entry_type='adjustment',
                unit_price=product.buying_price,
                total_amount=abs(quantity_diff) * product.buying_price,
                created_by=self.context['request'].user if 'request' in self.context else None,
                notes=f"Quantity adjustment via API: {old_quantity} → {new_quantity}"
            )
        
        return product


class StockEntrySerializer(serializers.ModelSerializer):
    """Serializer for stock entries"""
    
    product_detail = ProductListSerializer(source='product', read_only=True)
    entry_type_display = serializers.CharField(source='get_entry_type_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    is_stock_in = serializers.BooleanField(read_only=True)
    is_stock_out = serializers.BooleanField(read_only=True)
    absolute_quantity = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = StockEntry
        fields = [
            'id',
            'product',
            'product_detail',
            'quantity',
            'absolute_quantity',
            'entry_type',
            'entry_type_display',
            'unit_price',
            'total_amount',
            'reference_id',
            'notes',
            'created_by',
            'created_by_username',
            'created_at',
            'is_stock_in',
            'is_stock_out',
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate(self, data):
        """Validate stock entry"""
        product = data.get('product')
        quantity = data.get('quantity')
        entry_type = data.get('entry_type')
        
        # Quantity cannot be zero
        if quantity == 0:
            raise serializers.ValidationError({
                'quantity': 'Quantity cannot be zero'
            })
        
        # Validate single item quantities
        if product and product.category.is_single_item:
            if entry_type in ['purchase', 'return'] and abs(quantity) != 1:
                raise serializers.ValidationError({
                    'quantity': 'Single items must have quantity = 1 for purchases/returns'
                })
        
        # Validate sales don't exceed stock
        if entry_type == 'sale' and product:
            if abs(quantity) > product.quantity:
                raise serializers.ValidationError({
                    'quantity': f'Cannot sell {abs(quantity)} units. Only {product.quantity} available.'
                })
        
        # Validate single items cannot be restocked
        if product and product.category.is_single_item:
            if entry_type == 'purchase' and product.quantity > 0:
                raise serializers.ValidationError({
                    'entry_type': 'Single items cannot be restocked. Create a new product instead.'
                })
        
        # Auto-calculate total_amount if not provided
        if 'total_amount' not in data or not data['total_amount']:
            unit_price = data.get('unit_price')
            if unit_price:
                data['total_amount'] = abs(quantity) * unit_price
        
        return data
    
    def create(self, validated_data):
        """Create stock entry and update product quantity"""
        # Set created_by to current user
        if 'request' in self.context:
            validated_data['created_by'] = self.context['request'].user
        
        # Create stock entry (product quantity is updated in model's save method)
        stock_entry = super().create(validated_data)
        
        return stock_entry


class StockMovementSerializer(serializers.Serializer):
    """Serializer for stock movement operations (sale, purchase, etc.)"""
    
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField()
    entry_type = serializers.ChoiceField(choices=StockEntry.ENTRY_TYPE_CHOICES)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    reference_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_product_id(self, value):
        """Validate product exists"""
        try:
            Product.objects.get(id=value, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found or inactive")
        return value
    
    def validate(self, data):
        """Validate stock movement"""
        product = Product.objects.get(id=data['product_id'])
        quantity = data['quantity']
        entry_type = data['entry_type']
        
        # Set unit_price if not provided
        if 'unit_price' not in data:
            if entry_type in ['purchase', 'return']:
                data['unit_price'] = product.buying_price
            else:
                data['unit_price'] = product.selling_price
        
        # Validate quantity sign based on entry type
        if entry_type in ['purchase', 'return'] and quantity < 0:
            raise serializers.ValidationError({
                'quantity': 'Quantity must be positive for purchases and returns'
            })
        
        if entry_type == 'sale' and quantity > 0:
            raise serializers.ValidationError({
                'quantity': 'Quantity must be negative for sales'
            })
        
        # Validate stock availability for sales
        if entry_type == 'sale' and abs(quantity) > product.quantity:
            raise serializers.ValidationError({
                'quantity': f'Insufficient stock. Available: {product.quantity}'
            })
        
        return data
    
    def save(self):
        """Create stock entry"""
        product = Product.objects.get(id=self.validated_data['product_id'])
        
        stock_entry = StockEntry.objects.create(
            product=product,
            quantity=self.validated_data['quantity'],
            entry_type=self.validated_data['entry_type'],
            unit_price=self.validated_data['unit_price'],
            total_amount=abs(self.validated_data['quantity']) * self.validated_data['unit_price'],
            reference_id=self.validated_data.get('reference_id', ''),
            notes=self.validated_data.get('notes', ''),
            created_by=self.context.get('request').user if 'request' in self.context else None
        )
        
        return stock_entry


class BulkStockMovementSerializer(serializers.Serializer):
    """Serializer for bulk stock movements (multiple products at once)"""
    
    movements = StockMovementSerializer(many=True)
    
    def validate_movements(self, value):
        """Validate movements list is not empty"""
        if not value:
            raise serializers.ValidationError("At least one movement is required")
        return value
    
    def save(self):
        """Create multiple stock entries"""
        stock_entries = []
        
        for movement_data in self.validated_data['movements']:
            serializer = StockMovementSerializer(
                data=movement_data,
                context=self.context
            )
            serializer.is_valid(raise_exception=True)
            stock_entries.append(serializer.save())
        
        return stock_entries


class ProductStockSummarySerializer(serializers.Serializer):
    """Serializer for product stock summary/reports"""
    
    product_id = serializers.IntegerField()
    product_code = serializers.CharField()
    product_name = serializers.CharField()
    category = serializers.CharField()
    current_quantity = serializers.IntegerField()
    total_purchased = serializers.IntegerField()
    total_sold = serializers.IntegerField()
    total_returned = serializers.IntegerField()
    total_adjusted = serializers.IntegerField()
    inventory_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    profit_margin = serializers.DecimalField(max_digits=12, decimal_places=2)