# app/crud/product.py
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate, ProductStockUpdate


class CRUDProduct:
    def get(self, db: Session, product_id: int) -> Optional[Product]:
        return db.query(Product).filter(Product.id == product_id).first()
    
    def get_by_sku(self, db: Session, sku: str) -> Optional[Product]:
        return db.query(Product).filter(Product.sku == sku).first()
    
    def get_by_barcode(self, db: Session, barcode: str) -> Optional[Product]:
        return db.query(Product).filter(Product.barcode == barcode).first()
    
    def get_all(
        self, db: Session, skip: int = 0, limit: int = 100,
        category_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
        active_only: bool = True
    ) -> List[Product]:
        query = db.query(Product)
        
        if active_only:
            query = query.filter(Product.is_active == True)
        if category_id:
            query = query.filter(Product.category_id == category_id)
        if supplier_id:
            query = query.filter(Product.supplier_id == supplier_id)
        
        return query.offset(skip).limit(limit).all()
    
    def search(
        self, db: Session, search_term: str, skip: int = 0, limit: int = 100
    ) -> List[Product]:
        return db.query(Product).filter(
            or_(
                Product.name.ilike(f"%{search_term}%"),
                Product.sku.ilike(f"%{search_term}%"),
                Product.barcode.ilike(f"%{search_term}%"),
                Product.brand.ilike(f"%{search_term}%"),
                Product.description.ilike(f"%{search_term}%")
            )
        ).offset(skip).limit(limit).all()
    
    def get_low_stock(self, db: Session, skip: int = 0, limit: int = 100) -> List[Product]:
        return db.query(Product).filter(
            and_(
                Product.current_stock <= Product.min_stock_level,
                Product.is_active == True
            )
        ).offset(skip).limit(limit).all()
    
    def get_out_of_stock(self, db: Session, skip: int = 0, limit: int = 100) -> List[Product]:
        return db.query(Product).filter(
            and_(
                Product.current_stock == 0,
                Product.is_active == True
            )
        ).offset(skip).limit(limit).all()
    
    def create(self, db: Session, product: ProductCreate) -> Product:
        # Calculate margin
        margin = None
        if product.cost_price > 0:
            margin = float(((product.selling_price - product.cost_price) / product.cost_price) * 100)
        
        db_product = Product(
            sku=product.sku,
            name=product.name,
            description=product.description,
            category_id=product.category_id,
            supplier_id=product.supplier_id,
            cost_price=product.cost_price,
            selling_price=product.selling_price,
            margin=margin,
            current_stock=product.current_stock,
            min_stock_level=product.min_stock_level,
            max_stock_level=product.max_stock_level,
            unit_of_measure=product.unit_of_measure,
            brand=product.brand,
            model=product.model,
            weight=product.weight,
            dimensions=product.dimensions,
            barcode=product.barcode,
            is_active=product.is_active,
            is_taxable=product.is_taxable,
            tax_rate=product.tax_rate
        )
        
        # Set last_restocked if initial stock > 0
        if product.current_stock > 0:
            db_product.last_restocked = datetime.now()
        
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return db_product
    
    def update(
        self, db: Session, product_id: int, product: ProductUpdate
    ) -> Optional[Product]:
        db_product = self.get(db, product_id)
        if not db_product:
            return None
        
        update_data = product.model_dump(exclude_unset=True)
        
        # Recalculate margin if prices are updated
        if 'cost_price' in update_data or 'selling_price' in update_data:
            cost_price = update_data.get('cost_price', db_product.cost_price)
            selling_price = update_data.get('selling_price', db_product.selling_price)
            
            if cost_price > 0:
                margin = float(((selling_price - cost_price) / cost_price) * 100)
                update_data['margin'] = margin
        
        for field, value in update_data.items():
            setattr(db_product, field, value)
        
        db.commit()
        db.refresh(db_product)
        return db_product
    
    def update_stock(
        self, db: Session, product_id: int, stock_update: ProductStockUpdate
    ) -> Optional[Product]:
        db_product = self.get(db, product_id)
        if not db_product:
            return None
        
        new_stock = db_product.current_stock + stock_update.quantity
        
        # Check for negative stock
        if new_stock < 0:
            return None
        
        db_product.current_stock = new_stock
        
        # Update last_restocked if stock was added
        if stock_update.quantity > 0:
            db_product.last_restocked = datetime.now()
        
        db.commit()
        db.refresh(db_product)
        return db_product
    
    def bulk_update_stock(
        self, db: Session, stock_updates: Dict[int, int]
    ) -> Dict[int, bool]:
        results = {}
        for product_id, quantity in stock_updates.items():
            db_product = self.get(db, product_id)
            if db_product:
                new_stock = db_product.current_stock + quantity
                if new_stock >= 0:
                    db_product.current_stock = new_stock
                    if quantity > 0:
                        db_product.last_restocked = datetime.now()
                    results[product_id] = True
                else:
                    results[product_id] = False
            else:
                results[product_id] = False
        
        db.commit()
        return results
    
    def delete(self, db: Session, product_id: int) -> bool:
        db_product = self.get(db, product_id)
        if not db_product:
            return False
        
        # Instead of deleting, mark as inactive
        db_product.is_active = False
        db.commit()
        return True
    
    def get_inventory_summary(self, db: Session) -> Dict[str, Any]:
        """Get inventory summary statistics"""
        from sqlalchemy import func
        
        result = db.query(
            func.count(Product.id).label('total_products'),
            func.sum(Product.current_stock).label('total_stock'),
            func.sum(Product.current_stock * Product.cost_price).label('total_inventory_value'),
            func.sum(Product.current_stock * Product.selling_price).label('total_potential_revenue')
        ).filter(Product.is_active == True).first()
        
        low_stock_count = db.query(func.count(Product.id)).filter(
            and_(
                Product.current_stock <= Product.min_stock_level,
                Product.is_active == True
            )
        ).scalar()
        
        out_of_stock_count = db.query(func.count(Product.id)).filter(
            and_(
                Product.current_stock == 0,
                Product.is_active == True
            )
        ).scalar()
        
        return {
            'total_products': result.total_products or 0,
            'total_stock': result.total_stock or 0,
            'total_inventory_value': float(result.total_inventory_value or 0),
            'total_potential_revenue': float(result.total_potential_revenue or 0),
            'low_stock_count': low_stock_count or 0,
            'out_of_stock_count': out_of_stock_count or 0
        }
    def get_products_by_category_name(
        self, 
        db: Session, 
        category_name: str,
        skip: int = 0, 
        limit: int = 100
    ) -> List[Product]:
        """Get all products under a specific category by category name"""
        return db.query(Product).join(Category).filter(
            Category.name.ilike(f"%{category_name}%")
        ).filter(
            Product.is_active == True
        ).offset(skip).limit(limit).all()
    
    def get_products_by_supplier_name(
        self, 
        db: Session, 
        supplier_name: str,
        skip: int = 0, 
        limit: int = 100
    ) -> List[Product]:
        """Get all products from a specific supplier by supplier name"""
        return db.query(Product).join(Supplier).filter(
            Supplier.name.ilike(f"%{supplier_name}%")
        ).filter(
            Product.is_active == True
        ).offset(skip).limit(limit).all()
    
    def get_all_products_with_relations(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        category_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
        active_only: bool = True
    ) -> List[Product]:
        """Get all products with full category and supplier details"""
        query = db.query(Product)
        
        # Join with category and supplier
        query = query.join(Category, isouter=True).join(Supplier, isouter=True)
        
        if active_only:
            query = query.filter(Product.is_active == True)
        if category_id:
            query = query.filter(Product.category_id == category_id)
        if supplier_id:
            query = query.filter(Product.supplier_id == supplier_id)
        
        # Load relationships
        query = query.options(
            sqlalchemy.orm.selectinload(Product.category),
            sqlalchemy.orm.selectinload(Product.supplier)
        )
        
        return query.offset(skip).limit(limit).all()


product = CRUDProduct()