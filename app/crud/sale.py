# app/crud/sale.py
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, extract, desc
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
import uuid

from app.models.sale import Sale, SaleItem
from app.models.product import Product
from app.schemas.sale import SaleCreate, SaleUpdate, SaleStatus
from app.crud.product import product as product_crud


class CRUDSale:
    def generate_sale_number(self, db: Session) -> str:
        """Generate unique sale number: SAL-YYYYMMDD-001"""
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"SAL-{today}"
        
        # Find latest sale number for today
        last_sale = db.query(Sale).filter(
            Sale.sale_number.like(f"{prefix}-%")
        ).order_by(Sale.sale_number.desc()).first()
        
        if last_sale:
            last_num = int(last_sale.sale_number.split("-")[-1])
            new_num = f"{prefix}-{last_num + 1:03d}"
        else:
            new_num = f"{prefix}-001"
        
        return new_num
    
    def get(self, db: Session, sale_id: int) -> Optional[Sale]:
        return db.query(Sale).filter(Sale.id == sale_id).first()
    
    def get_by_number(self, db: Session, sale_number: str) -> Optional[Sale]:
        return db.query(Sale).filter(Sale.sale_number == sale_number).first()
    
    def get_all(
        self, db: Session, 
        skip: int = 0, limit: int = 100,
        status: Optional[str] = None,
        payment_status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Sale]:
        query = db.query(Sale)
        
        if status:
            query = query.filter(Sale.status == status)
        if payment_status:
            query = query.filter(Sale.payment_status == payment_status)
        if start_date:
            query = query.filter(Sale.sale_date >= start_date)
        if end_date:
            query = query.filter(Sale.sale_date <= end_date)
        
        return query.order_by(desc(Sale.sale_date)).offset(skip).limit(limit).all()
    
    def get_sales_by_date_range(
        self, db: Session, 
        start_date: date, end_date: date
    ) -> List[Sale]:
        return db.query(Sale).filter(
            and_(
                func.date(Sale.sale_date) >= start_date,
                func.date(Sale.sale_date) <= end_date
            )
        ).order_by(Sale.sale_date).all()
    
    def create(self, db: Session, sale: SaleCreate, user_id: Optional[int] = None) -> Tuple[Optional[Sale], str]:
        """Create a new sale with automatic stock updates"""
        try:
            # Generate sale number
            sale_number = self.generate_sale_number(db)
            
            # Create sale object
            db_sale = Sale(
                sale_number=sale_number,
                customer_name=sale.customer_name,
                customer_email=sale.customer_email,
                customer_phone=sale.customer_phone,
                payment_method=sale.payment_method.value,
                payment_status=sale.payment_status.value,
                payment_reference=sale.payment_reference,
                status=sale.status.value,
                shipping_address=sale.shipping_address,
                shipping_city=sale.shipping_city,
                shipping_state=sale.shipping_state,
                shipping_country=sale.shipping_country,
                shipping_pincode=sale.shipping_pincode,
                notes=sale.notes,
                user_id=user_id
            )
            
            # Initialize totals
            total_amount = Decimal('0.00')
            total_tax = Decimal('0.00')
            total_discount = Decimal('0.00')
            
            # Process each sale item
            for item_data in sale.items:
                # Get product with lock to prevent race conditions
                product = db.query(Product).with_for_update().filter(
                    Product.id == item_data.product_id
                ).first()
                
                if not product:
                    return None, f"Product ID {item_data.product_id} not found"
                
                # Check stock availability
                if product.current_stock < item_data.quantity:
                    return None, f"Insufficient stock for {product.name}. Available: {product.current_stock}"
                
                # Calculate item amounts
                subtotal = Decimal(str(item_data.unit_price)) * item_data.quantity
                discount_amount = subtotal * (Decimal(str(item_data.discount_percent)) / Decimal('100'))
                taxable_amount = subtotal - discount_amount
                tax_amount = taxable_amount * (Decimal(str(item_data.tax_rate)) / Decimal('100'))
                item_total = taxable_amount + tax_amount
                
                # Create sale item with product snapshot
                sale_item = SaleItem(
                    sale=db_sale,
                    product_id=product.id,
                    quantity=item_data.quantity,
                    unit_price=item_data.unit_price,
                    tax_rate=item_data.tax_rate,
                    tax_amount=tax_amount,
                    discount_percent=item_data.discount_percent,
                    discount_amount=discount_amount,
                    subtotal=subtotal,
                    total=item_total,
                    product_name=product.name,
                    product_sku=product.sku,
                    product_barcode=product.barcode
                )
                
                # Update totals
                total_amount += subtotal
                total_tax += tax_amount
                total_discount += discount_amount
                
                # Deduct stock from inventory
                product.current_stock -= item_data.quantity
                db.add(product)
                db.add(sale_item)
            
            # Set sale totals
            db_sale.total_amount = total_amount
            db_sale.tax_amount = total_tax
            db_sale.discount_amount = total_discount
            db_sale.grand_total = total_amount + total_tax - total_discount
            
            # Auto-complete payment if cash
            if sale.payment_method.value == "cash" and sale.status.value == "completed":
                db_sale.payment_status = "paid"
            
            db.add(db_sale)
            db.commit()
            db.refresh(db_sale)
            
            return db_sale, "Sale created successfully"
            
        except Exception as e:
            db.rollback()
            return None, f"Error creating sale: {str(e)}"
    
    def update(
        self, db: Session, sale_id: int, sale: SaleUpdate
    ) -> Tuple[Optional[Sale], str]:
        db_sale = self.get(db, sale_id)
        if not db_sale:
            return None, "Sale not found"
        
        # Cannot update completed/cancelled sales
        if db_sale.status in ["completed", "cancelled"]:
            return None, f"Cannot update {db_sale.status} sale"
        
        update_data = sale.model_dump(exclude_unset=True)
        
        # Convert enum values to strings
        for field in ['payment_method', 'payment_status', 'status']:
            if field in update_data:
                update_data[field] = update_data[field].value
        
        for field, value in update_data.items():
            setattr(db_sale, field, value)
        
        db.commit()
        db.refresh(db_sale)
        return db_sale, "Sale updated successfully"
    
    def cancel(self, db: Session, sale_id: int) -> Tuple[bool, str]:
        """Cancel a sale and restore stock"""
        db_sale = self.get(db, sale_id)
        if not db_sale:
            return False, "Sale not found"
        
        if db_sale.status == "cancelled":
            return False, "Sale is already cancelled"
        
        try:
            # Restore stock for each item
            for item in db_sale.items:
                product = product_crud.get(db, item.product_id)
                if product:
                    product.current_stock += item.quantity
                    db.add(product)
            
            # Update sale status
            db_sale.status = "cancelled"
            db_sale.payment_status = "refunded" if db_sale.payment_status == "paid" else "pending"
            
            db.commit()
            return True, "Sale cancelled successfully"
            
        except Exception as e:
            db.rollback()
            return False, f"Error cancelling sale: {str(e)}"
    
    def delete(self, db: Session, sale_id: int) -> bool:
        """Delete a sale (only drafts can be deleted)"""
        db_sale = self.get(db, sale_id)
        if not db_sale or db_sale.status != "draft":
            return False
        
        db.delete(db_sale)
        db.commit()
        return True
    
    def get_sales_summary(self, db: Session) -> Dict[str, Any]:
        """Get sales summary for dashboard"""
        today = date.today()
        
        # Total sales count
        total_sales = db.query(func.count(Sale.id)).filter(
            Sale.status == "completed"
        ).scalar() or 0
        
        # Total revenue
        total_revenue_result = db.query(func.sum(Sale.grand_total)).filter(
            Sale.status == "completed"
        ).first()
        total_revenue = total_revenue_result[0] or Decimal('0.00')
        
        # Average order value
        avg_order_value = total_revenue / total_sales if total_sales > 0 else Decimal('0.00')
        
        # Today's sales
        today_sales = db.query(func.count(Sale.id)).filter(
            and_(
                Sale.status == "completed",
                func.date(Sale.sale_date) == today
            )
        ).scalar() or 0
        
        # Today's revenue
        today_revenue_result = db.query(func.sum(Sale.grand_total)).filter(
            and_(
                Sale.status == "completed",
                func.date(Sale.sale_date) == today
            )
        ).first()
        today_revenue = today_revenue_result[0] or Decimal('0.00')
        
        # Most sold products (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        most_sold = db.query(
            SaleItem.product_name,
            func.sum(SaleItem.quantity).label('total_quantity'),
            func.sum(SaleItem.total).label('total_revenue')
        ).join(Sale).filter(
            and_(
                Sale.status == "completed",
                Sale.sale_date >= thirty_days_ago
            )
        ).group_by(
            SaleItem.product_name
        ).order_by(
            desc('total_quantity')
        ).limit(10).all()
        
        most_sold_products = [
            {
                "name": item.product_name,
                "quantity": item.total_quantity,
                "revenue": float(item.total_revenue)
            }
            for item in most_sold
        ]
        
        return {
            'total_sales': total_sales,
            'total_revenue': float(total_revenue),
            'avg_order_value': float(avg_order_value),
            'today_sales': today_sales,
            'today_revenue': float(today_revenue),
            'most_sold_products': most_sold_products
        }
    
    def get_daily_sales(self, db: Session, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily sales for chart"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        daily_sales = db.query(
            func.date(Sale.sale_date).label('date'),
            func.count(Sale.id).label('sales_count'),
            func.sum(Sale.grand_total).label('total_revenue')
        ).filter(
            and_(
                Sale.status == "completed",
                func.date(Sale.sale_date) >= start_date.date(),
                func.date(Sale.sale_date) <= end_date.date()
            )
        ).group_by(
            func.date(Sale.sale_date)
        ).order_by(
            'date'
        ).all()
        
        return [
            {
                'date': row.date,
                'sales_count': row.sales_count or 0,
                'total_revenue': float(row.total_revenue or 0)
            }
            for row in daily_sales
        ]
    
    def get_sales_by_product(
        self, db: Session, 
        product_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get sales report by product"""
        query = db.query(
            SaleItem.product_id,
            SaleItem.product_name,
            SaleItem.product_sku,
            func.sum(SaleItem.quantity).label('total_quantity'),
            func.sum(SaleItem.total).label('total_revenue'),
            func.avg(SaleItem.unit_price).label('avg_price')
        ).join(Sale).filter(
            Sale.status == "completed"
        )
        
        if product_id:
            query = query.filter(SaleItem.product_id == product_id)
        
        if start_date:
            query = query.filter(func.date(Sale.sale_date) >= start_date)
        
        if end_date:
            query = query.filter(func.date(Sale.sale_date) <= end_date)
        
        results = query.group_by(
            SaleItem.product_id,
            SaleItem.product_name,
            SaleItem.product_sku
        ).order_by(
            desc('total_quantity')
        ).all()
        
        return [
            {
                'product_id': row.product_id,
                'product_name': row.product_name,
                'product_sku': row.product_sku,
                'total_quantity': row.total_quantity or 0,
                'total_revenue': float(row.total_revenue or 0),
                'avg_price': float(row.avg_price or 0)
            }
            for row in results
        ]


sale = CRUDSale()