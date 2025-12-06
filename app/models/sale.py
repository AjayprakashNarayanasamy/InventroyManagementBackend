# app/models/sale.py
from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, ForeignKey, Text, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.database import Base


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    sale_number = Column(String(50), unique=True, index=True, nullable=False)
    customer_name = Column(String(100), nullable=True)
    customer_email = Column(String(100), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    
    # Sale details
    total_amount = Column(DECIMAL(10, 2), nullable=False, default=0.00)
    tax_amount = Column(DECIMAL(10, 2), nullable=False, default=0.00)
    discount_amount = Column(DECIMAL(10, 2), nullable=False, default=0.00)
    grand_total = Column(DECIMAL(10, 2), nullable=False, default=0.00)
    
    # Payment details
    payment_method = Column(String(50), nullable=False, default="cash")
    payment_status = Column(String(20), nullable=False, default="pending")
    payment_reference = Column(String(100), nullable=True)
    
    # Sale status
    status = Column(String(20), nullable=False, default="completed")
    
    # Shipping details
    shipping_address = Column(Text, nullable=True)
    shipping_city = Column(String(50), nullable=True)
    shipping_state = Column(String(50), nullable=True)
    shipping_country = Column(String(50), nullable=True)
    shipping_pincode = Column(String(10), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    sale_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    user = relationship("User", backref="sales")
    
    def __repr__(self):
        return f"<Sale(id={self.id}, sale_number='{self.sale_number}', total={self.grand_total})>"


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    sale_id = Column(Integer, ForeignKey("sales.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Item details
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    tax_rate = Column(Float, nullable=False, default=18.0)
    tax_amount = Column(DECIMAL(10, 2), nullable=False, default=0.00)
    discount_percent = Column(Float, nullable=False, default=0.00)
    discount_amount = Column(DECIMAL(10, 2), nullable=False, default=0.00)
    subtotal = Column(DECIMAL(10, 2), nullable=False)
    total = Column(DECIMAL(10, 2), nullable=False)
    
    # Product snapshot
    product_name = Column(String(200), nullable=False)
    product_sku = Column(String(50), nullable=False)
    product_barcode = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    sale = relationship("Sale", back_populates="items")
    product = relationship("Product", backref="sale_items")
    
    def __repr__(self):
        return f"<SaleItem(id={self.id}, product='{self.product_name}', quantity={self.quantity})>"