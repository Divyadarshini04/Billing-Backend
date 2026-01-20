from rest_framework import serializers
from .models import Category, Product, validate_tax_rate, validate_stock_non_negative
from apps.purchase.models import Supplier

class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category with validation."""
    
    class Meta:
        model = Category
        fields = ["id", "name", "description", "color", "is_active", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]
    
    def validate_name(self, value):
        """Validate category name is unique."""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Category name cannot be empty")
        return value

class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product with comprehensive validation."""
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        required=False,
        allow_null=True
    )
    preferred_supplier_name = serializers.CharField(source='preferred_supplier.name', read_only=True)
    preferred_supplier_id = serializers.PrimaryKeyRelatedField(
        queryset=Supplier.objects.all(),
        source="preferred_supplier",
        write_only=True,
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = Product
        fields = [
            "id",
            "product_code",
            "name",
            "hsn_code",
            "unit",
            "category",
            "category_id",
            "preferred_supplier_name",
            "preferred_supplier_id",
            "cost_price",
            "unit_price",
            "tax_rate",
            "reorder_level",
            "reorder_quantity",
            "stock",
            "is_active",
            "created_at",
            "updated_at"
        ]
        read_only_fields = ["created_at", "updated_at", "id"]
    
    def validate_product_code(self, value):
        """Validate product code is not empty and unique."""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Product code cannot be empty")
        return value
    
    def validate_name(self, value):
        """Validate product name is not empty."""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Product name cannot be empty")
        return value
    
    def validate_unit_price(self, value):
        """Validate unit price is non-negative."""
        if value < 0:
            raise serializers.ValidationError("Unit price cannot be negative")
        return value
    
    def validate_tax_rate(self, value):
        """Validate tax rate is between 0-100."""
        try:
            validate_tax_rate(value)
        except Exception as e:
            raise serializers.ValidationError(str(e))
        return value
    
    def validate_stock(self, value):
        """Validate stock cannot be negative."""
        try:
            validate_stock_non_negative(value)
        except Exception as e:
            raise serializers.ValidationError(str(e))
        return value
    
    def validate_reorder_level(self, value):
        """Validate reorder level is non-negative."""
        if value < 0:
            raise serializers.ValidationError("Reorder level cannot be negative")
        return value
