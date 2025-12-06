# app/schemas/product.py
from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from typing import Optional, Dict, Any 
from decimal import Decimal
from pydantic.types import condecimal


class ProductBase(BaseModel):
    sku: str = Field(..., min_length=1, max_length=50, description="Stock Keeping Unit (unique)")
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    
    # Foreign keys
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None
    
    # Pricing - Use condecimal for decimal places
    cost_price: Decimal = Field(default=Decimal('0.00'), ge=0)
    selling_price: Decimal = Field(default=Decimal('0.00'), ge=0)
    
    # Inventory tracking
    current_stock: int = Field(default=0, ge=0)
    min_stock_level: int = Field(default=10, ge=0)
    max_stock_level: int = Field(default=100, ge=1)
    unit_of_measure: str = Field(default="pcs", max_length=20)
    
    # Product details
    brand: Optional[str] = Field(default=None, max_length=100)
    model: Optional[str] = Field(default=None, max_length=100)
    weight: Optional[float] = Field(default=None, ge=0)
    dimensions: Optional[str] = Field(default=None, max_length=50)
    barcode: Optional[str] = Field(default=None, max_length=100)
    
    # Status and metadata
    is_active: bool = Field(default=True)
    is_taxable: bool = Field(default=True)
    tax_rate: float = Field(default=18.0, ge=0, le=100)
    
    @field_validator('selling_price')
    def validate_selling_price(cls, v, info):
        if 'cost_price' in info.data and v < info.data['cost_price']:
            raise ValueError('Selling price cannot be less than cost price')
        return v
    
    @field_validator('max_stock_level')
    def validate_stock_levels(cls, v, info):
        if 'min_stock_level' in info.data and v <= info.data['min_stock_level']:
            raise ValueError('Max stock level must be greater than min stock level')
        return v
    
    @field_validator('cost_price', 'selling_price')
    def round_decimal_fields(cls, v):
        """Round decimal fields to 2 decimal places"""
        if isinstance(v, Decimal):
            return round(v, 2)
        return v


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku: Optional[str] = Field(default=None, min_length=1, max_length=50)
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None
    cost_price: Optional[Decimal] = Field(default=None, ge=0)
    selling_price: Optional[Decimal] = Field(default=None, ge=0)
    current_stock: Optional[int] = Field(default=None, ge=0)
    min_stock_level: Optional[int] = Field(default=None, ge=0)
    max_stock_level: Optional[int] = Field(default=None, ge=1)
    unit_of_measure: Optional[str] = Field(default=None, max_length=20)
    brand: Optional[str] = Field(default=None, max_length=100)
    model: Optional[str] = Field(default=None, max_length=100)
    weight: Optional[float] = Field(default=None, ge=0)
    dimensions: Optional[str] = Field(default=None, max_length=50)
    barcode: Optional[str] = Field(default=None, max_length=100)
    is_active: Optional[bool] = None
    is_taxable: Optional[bool] = None
    tax_rate: Optional[float] = Field(default=None, ge=0, le=100)


class Product(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    margin: Optional[float] = None  # Auto-calculated
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_restocked: Optional[datetime] = None
    
    # Relationships (will be populated)
    category_name: Optional[str] = None
    supplier_name: Optional[str] = None


class ProductStockUpdate(BaseModel):
    """Schema for updating stock levels"""
    quantity: int = Field(..., description="Positive for addition, negative for deduction")
    notes: Optional[str] = None



# Update or add this class
class ProductWithRelations(Product):
    """Product with full category and supplier details including all columns"""
    model_config = ConfigDict(from_attributes=True)
    
    # Include all category fields
    category: Optional[Dict[str, Any]] = None
    # Include all supplier fields
    supplier: Optional[Dict[str, Any]] = None