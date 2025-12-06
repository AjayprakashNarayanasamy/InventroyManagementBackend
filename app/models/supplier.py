# app/models/supplier.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from app.database.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    contact_person = Column(String(100), nullable=True)
    email = Column(String(100), nullable=True, index=True)
    phone = Column(String(20), nullable=True)
    
    # Address fields
    address = Column(Text, nullable=True)
    city = Column(String(50), nullable=True)
    state = Column(String(50), nullable=True)
    country = Column(String(50), nullable=True, default="India")
    postal_code = Column(String(20), nullable=True)
    
    # Business details
    tax_id = Column(String(50), nullable=True)  # GST/VAT number
    website = Column(String(100), nullable=True)
    
    # Status and metadata
    is_active = Column(Boolean, default=True)
    payment_terms = Column(String(100), nullable=True)  # e.g., "Net 30", "COD"
    rating = Column(Integer, default=5)  # 1-5 rating
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Supplier(id={self.id}, name='{self.name}')>"