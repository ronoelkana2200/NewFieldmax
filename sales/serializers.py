from rest_framework import serializers
from .models import Sale, Product

class SaleSerializer(serializers.ModelSerializer):
    seller_username = serializers.CharField(source='seller.username', read_only=True)

    class Meta:
        model = Sale
        fields = ['sale_id', 'sale_date', 'total_amount', 'seller', 'seller_username', 'client_details', 'product_code', 'items']
