# app/schemas/supplier.py
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime
from typing import Optional


class SupplierBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    contact_person: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    
    # Address fields
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=50)
    state: Optional[str] = Field(None, max_length=50)
    country: Optional[str] = Field(None, max_length=50)
    postal_code: Optional[str] = Field(None, max_length=20)
    
    # Business details
    tax_id: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=100)
    
    # Status and metadata
    is_active: Optional[bool] = True
    payment_terms: Optional[str] = Field(None, max_length=100)
    rating: Optional[int] = Field(5, ge=1, le=5)  # Rating between 1-5
    notes: Optional[str] = None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    contact_person: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=50)
    state: Optional[str] = Field(None, max_length=50)
    country: Optional[str] = Field(None, max_length=50)
    postal_code: Optional[str] = Field(None, max_length=20)
    tax_id: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    payment_terms: Optional[str] = Field(None, max_length=100)
    rating: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = None


class Supplier(SupplierBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None