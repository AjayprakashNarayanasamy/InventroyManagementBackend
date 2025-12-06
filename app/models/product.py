# app/models/product.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, DECIMAL, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), unique=True, index=True, nullable=False)  # Stock Keeping Unit
    name = Column(String(200), index=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Foreign keys
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    
    # Pricing
    cost_price = Column(DECIMAL(10, 2), nullable=False, default=0.00)  # Cost from supplier
    selling_price = Column(DECIMAL(10, 2), nullable=False, default=0.00)  # Selling price
    margin = Column(Float, nullable=True)  # Auto-calculated: ((selling_price - cost_price) / cost_price) * 100
    
    # Inventory tracking
    current_stock = Column(Integer, nullable=False, default=0)
    min_stock_level = Column(Integer, nullable=False, default=10)  # Reorder point
    max_stock_level = Column(Integer, nullable=False, default=100)
    unit_of_measure = Column(String(20), nullable=False, default="pcs")  # pcs, kg, liters, etc.
    
    # Product details
    brand = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    weight = Column(Float, nullable=True)  # in kg
    dimensions = Column(String(50), nullable=True)  # "10x20x30 cm"
    barcode = Column(String(100), nullable=True, unique=True, index=True)
    
    # Status and metadata
    is_active = Column(Boolean, default=True)
    is_taxable = Column(Boolean, default=True)
    tax_rate = Column(Float, default=18.0)  # GST/VAT percentage
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_restocked = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    category = relationship("Category", backref="products")
    supplier = relationship("Supplier", backref="products")
    
    # Check constraints
    __table_args__ = (
        CheckConstraint('selling_price >= 0', name='check_selling_price_positive'),
        CheckConstraint('cost_price >= 0', name='check_cost_price_positive'),
        CheckConstraint('current_stock >= 0', name='check_current_stock_positive'),
        CheckConstraint('selling_price >= cost_price', name='check_selling_price_gte_cost'),
        CheckConstraint('max_stock_level > min_stock_level', name='check_max_gt_min_stock'),
    )
    
    def __repr__(self):
        return f"<Product(id={self.id}, sku='{self.sku}', name='{self.name}')>"