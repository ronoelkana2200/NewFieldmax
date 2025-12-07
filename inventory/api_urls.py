from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet, SKUViewSet, StockEntryViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'skus', SKUViewSet)
router.register(r'stockentries', StockEntryViewSet)

urlpatterns = router.urls
