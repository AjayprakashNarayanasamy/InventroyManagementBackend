# app/schemas/sale.py
from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from enum import Enum


# Enums for validation
class PaymentMethod(str, Enum):
    CASH = "cash"
    CARD = "card"
    UPI = "upi"
    BANK_TRANSFER = "bank_transfer"
    CHEQUE = "cheque"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"
    REFUNDED = "refunded"


class SaleStatus(str, Enum):
    DRAFT = "draft"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Item schemas
class SaleItemBase(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0, description="Quantity must be greater than 0")
    unit_price: Decimal = Field(..., ge=0)
    tax_rate: float = Field(default=18.0, ge=0, le=100)
    discount_percent: float = Field(default=0.0, ge=0, le=100)
    
    @field_validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        return v


class SaleItemCreate(SaleItemBase):
    pass


class SaleItem(SaleItemBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    product_name: str
    product_sku: str
    tax_amount: Decimal
    discount_amount: Decimal
    subtotal: Decimal
    total: Decimal
    created_at: datetime


# Sale schemas
class SaleBase(BaseModel):
    customer_name: Optional[str] = Field(None, max_length=100)
    customer_email: Optional[str] = Field(None, max_length=100)
    customer_phone: Optional[str] = Field(None, max_length=20)
    payment_method: PaymentMethod = PaymentMethod.CASH
    payment_status: PaymentStatus = PaymentStatus.PENDING
    payment_reference: Optional[str] = Field(None, max_length=100)
    status: SaleStatus = SaleStatus.COMPLETED
    shipping_address: Optional[str] = None
    shipping_city: Optional[str] = Field(None, max_length=50)
    shipping_state: Optional[str] = Field(None, max_length=50)
    shipping_country: Optional[str] = Field(None, max_length=50)
    shipping_pincode: Optional[str] = Field(None, max_length=10)
    notes: Optional[str] = None
    user_id: Optional[int] = None


class SaleCreate(SaleBase):
    items: List[SaleItemCreate] = Field(..., min_items=1, description="At least one item required")


class SaleUpdate(BaseModel):
    customer_name: Optional[str] = Field(None, max_length=100)
    customer_email: Optional[str] = Field(None, max_length=100)
    customer_phone: Optional[str] = Field(None, max_length=20)
    payment_method: Optional[PaymentMethod] = None
    payment_status: Optional[PaymentStatus] = None
    payment_reference: Optional[str] = Field(None, max_length=100)
    status: Optional[SaleStatus] = None
    shipping_address: Optional[str] = None
    shipping_city: Optional[str] = Field(None, max_length=50)
    shipping_state: Optional[str] = Field(None, max_length=50)
    shipping_country: Optional[str] = Field(None, max_length=50)
    shipping_pincode: Optional[str] = Field(None, max_length=10)
    notes: Optional[str] = None


class Sale(SaleBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    sale_number: str
    total_amount: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    grand_total: Decimal
    sale_date: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Relationships
    items: List[SaleItem] = []
    user_name: Optional[str] = None


class SaleWithItems(Sale):
    """Sale with full item details"""
    pass


class SaleSummary(BaseModel):
    """Sales summary for reporting"""
    total_sales: int
    total_revenue: Decimal
    avg_order_value: Decimal
    today_sales: int
    today_revenue: Decimal
    most_sold_products: List[dict]


class DailySales(BaseModel):
    date: datetime
    total_sales: int
    total_revenue: Decimal