from django.urls import path
from .views import ProductListCreate, ProductRetrieveUpdateDelete, CategoryListCreate, CategoryRetrieveUpdateDelete, CheckStockAlertsView

urlpatterns = [
    path("products/", ProductListCreate.as_view(), name="product-list-create"),
    path("products/<int:pk>/", ProductRetrieveUpdateDelete.as_view(), name="product-detail"),
    path("categories/", CategoryListCreate.as_view(), name="category-list-create"),
    path("categories/<int:pk>/", CategoryRetrieveUpdateDelete.as_view(), name="category-detail"),
    path("check-alerts/", CheckStockAlertsView.as_view(), name="check-stock-alerts"),
]
