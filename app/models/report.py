# app/services/report_service.py
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal
import os
import json
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
import io
import tempfile

from app.models.sale import Sale, SaleItem
from app.models.product import Product
from app.models.category import Category
from app.models.supplier import Supplier
from app.models.user import User


class ReportService:
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== SALES REPORTS ====================
    
    def generate_sales_report(
        self, 
        start_date: date, 
        end_date: date,
        group_by: str = "day"
    ) -> Dict[str, Any]:
        """
        Generate sales report grouped by specified period
        """
        # Base query
        query = self.db.query(Sale).filter(
            and_(
                Sale.status == "completed",
                func.date(Sale.sale_date) >= start_date,
                func.date(Sale.sale_date) <= end_date
            )
        )
        
        # Get raw data
        sales = query.all()
        
        if not sales:
            return {
                "message": "No sales data found for the specified period",
                "data": []
            }
        
        # Convert to list of dictionaries for pandas
        sales_data = []
        for sale in sales:
            sales_data.append({
                "sale_id": sale.id,
                "sale_number": sale.sale_number,
                "sale_date": sale.sale_date,
                "customer_name": sale.customer_name,
                "total_amount": float(sale.total_amount),
                "tax_amount": float(sale.tax_amount),
                "discount_amount": float(sale.discount_amount),
                "grand_total": float(sale.grand_total),
                "payment_method": sale.payment_method,
                "payment_status": sale.payment_status,
                "items_count": len(sale.items)
            })
        
        # Create pandas DataFrame
        df = pd.DataFrame(sales_data)
        
        # Group by specified period
        if group_by == "day":
            df['period'] = df['sale_date'].dt.date
            group_col = 'period'
        elif group_by == "week":
            df['period'] = df['sale_date'].dt.strftime('%Y-W%U')
            group_col = 'period'
        elif group_by == "month":
            df['period'] = df['sale_date'].dt.strftime('%Y-%m')
            group_col = 'period'
        elif group_by == "product":
            # Need to get product data
            return self._generate_sales_by_product_report(start_date, end_date)
        else:
            df['period'] = "All"
            group_col = 'period'
        
        # Group and aggregate
        grouped = df.groupby(group_col).agg({
            'sale_id': 'count',
            'grand_total': ['sum', 'mean'],
            'items_count': 'sum'
        }).round(2)
        
        # Flatten column names
        grouped.columns = ['sales_count', 'total_revenue', 'avg_order_value', 'total_items']
        
        # Convert to list of dictionaries
        result_data = []
        for idx, row in grouped.iterrows():
            result_data.append({
                'period': idx,
                'sales_count': int(row['sales_count']),
                'total_revenue': float(row['total_revenue']),
                'avg_order_value': float(row['avg_order_value']),
                'total_items': int(row['total_items'])
            })
        
        # Calculate summary statistics
        summary = {
            'total_sales': int(df['sale_id'].count()),
            'total_revenue': float(df['grand_total'].sum()),
            'avg_order_value': float(df['grand_total'].mean()),
            'max_order': float(df['grand_total'].max()),
            'min_order': float(df['grand_total'].min()),
            'total_customers': df['customer_name'].nunique(),
            'payment_methods': df['payment_method'].value_counts().to_dict()
        }
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': (end_date - start_date).days + 1
            },
            'group_by': group_by,
            'summary': summary,
            'data': result_data,
            'total_products_sold': int(df['items_count'].sum())
        }
    
    def _generate_sales_by_product_report(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Generate sales report by product"""
        query = self.db.query(
            SaleItem.product_name,
            SaleItem.product_sku,
            func.sum(SaleItem.quantity).label('total_quantity'),
            func.sum(SaleItem.total).label('total_revenue'),
            func.avg(SaleItem.unit_price).label('avg_price')
        ).join(Sale).filter(
            and_(
                Sale.status == "completed",
                func.date(Sale.sale_date) >= start_date,
                func.date(Sale.sale_date) <= end_date
            )
        ).group_by(
            SaleItem.product_name,
            SaleItem.product_sku
        ).order_by(
            func.sum(SaleItem.total).desc()
        )
        
        results = query.all()
        
        data = []
        for row in results:
            data.append({
                'product_name': row.product_name,
                'product_sku': row.product_sku,
                'total_quantity': int(row.total_quantity),
                'total_revenue': float(row.total_revenue),
                'avg_price': float(row.avg_price)
            })
        
        # Create DataFrame for summary
        df = pd.DataFrame(data)
        
        summary = {}
        if not df.empty:
            summary = {
                'total_products': len(df),
                'total_quantity': int(df['total_quantity'].sum()),
                'total_revenue': float(df['total_revenue'].sum()),
                'top_product': df.iloc[0]['product_name'] if len(df) > 0 else None,
                'top_product_revenue': float(df.iloc[0]['total_revenue']) if len(df) > 0 else None
            }
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'group_by': 'product',
            'summary': summary,
            'data': data
        }
    
    # ==================== INVENTORY REPORTS ====================
    
    def generate_inventory_report(
        self,
        report_type: str = "stock_summary",
        threshold: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate inventory reports
        """
        query = self.db.query(Product).filter(Product.is_active == True)
        
        if report_type == "low_stock":
            query = query.filter(Product.current_stock <= Product.min_stock_level)
        elif report_type == "out_of_stock":
            query = query.filter(Product.current_stock == 0)
        elif report_type == "slow_moving":
            # Products with stock but no recent sales (simplified)
            query = query.filter(Product.current_stock > 0)
        
        products = query.all()
        
        # Convert to list of dictionaries
        inventory_data = []
        for product in products:
            stock_value = float(product.current_stock * product.cost_price)
            selling_value = float(product.current_stock * product.selling_price)
            
            inventory_data.append({
                'product_id': product.id,
                'sku': product.sku,
                'name': product.name,
                'category': product.category.name if product.category else 'N/A',
                'supplier': product.supplier.name if product.supplier else 'N/A',
                'current_stock': product.current_stock,
                'min_stock_level': product.min_stock_level,
                'max_stock_level': product.max_stock_level,
                'cost_price': float(product.cost_price),
                'selling_price': float(product.selling_price),
                'stock_value': stock_value,
                'selling_value': selling_value,
                'stock_status': self._get_stock_status(
                    product.current_stock, 
                    product.min_stock_level
                )
            })
        
        # Create DataFrame
        df = pd.DataFrame(inventory_data)
        
        # Calculate summary
        summary = {}
        if not df.empty:
            summary = {
                'total_products': len(df),
                'total_stock_units': int(df['current_stock'].sum()),
                'total_stock_value': float(df['stock_value'].sum()),
                'total_selling_value': float(df['selling_value'].sum()),
                'avg_stock_level': float(df['current_stock'].mean()),
                'low_stock_count': int((df['current_stock'] <= df['min_stock_level']).sum()),
                'out_of_stock_count': int((df['current_stock'] == 0).sum()),
                'over_stock_count': int((df['current_stock'] > df['max_stock_level']).sum())
            }
        
        return {
            'report_type': report_type,
            'generated_at': datetime.now(),
            'summary': summary,
            'data': inventory_data
        }
    
    def _get_stock_status(self, current_stock: int, min_stock: int) -> str:
        """Get stock status based on current level"""
        if current_stock == 0:
            return "Out of Stock"
        elif current_stock <= min_stock:
            return "Low Stock"
        elif current_stock <= min_stock * 2:
            return "Adequate"
        else:
            return "Over Stock"
    
    # ==================== PRODUCT REPORTS ====================
    
    def generate_product_report(
        self,
        category_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
        include_inactive: bool = False
    ) -> Dict[str, Any]:
        """
        Generate product report with filtering
        """
        query = self.db.query(Product)
        
        if not include_inactive:
            query = query.filter(Product.is_active == True)
        
        if category_id:
            query = query.filter(Product.category_id == category_id)
        
        if supplier_id:
            query = query.filter(Product.supplier_id == supplier_id)
        
        # Join with category and supplier
        query = query.join(Category, isouter=True).join(Supplier, isouter=True)
        
        products = query.all()
        
        # Convert to list of dictionaries
        product_data = []
        for product in products:
            margin = None
            if product.cost_price > 0:
                margin = float(((product.selling_price - product.cost_price) / product.cost_price) * 100)
            
            product_data.append({
                'product_id': product.id,
                'sku': product.sku,
                'name': product.name,
                'description': product.description,
                'category': product.category.name if product.category else 'N/A',
                'supplier': product.supplier.name if product.supplier else 'N/A',
                'brand': product.brand,
                'model': product.model,
                'current_stock': product.current_stock,
                'cost_price': float(product.cost_price),
                'selling_price': float(product.selling_price),
                'margin_percent': margin,
                'stock_value': float(product.current_stock * product.cost_price),
                'is_active': product.is_active,
                'last_restocked': product.last_restocked,
                'created_at': product.created_at
            })
        
        # Create DataFrame
        df = pd.DataFrame(product_data)
        
        # Calculate summary
        summary = {}
        if not df.empty:
            summary = {
                'total_products': len(df),
                'active_products': int(df['is_active'].sum()),
                'total_stock_value': float(df['stock_value'].sum()),
                'avg_cost_price': float(df['cost_price'].mean()),
                'avg_selling_price': float(df['selling_price'].mean()),
                'avg_margin': float(df['margin_percent'].mean()) if 'margin_percent' in df else None,
                'categories_count': df['category'].nunique(),
                'suppliers_count': df['supplier'].nunique()
            }
        
        return {
            'filters': {
                'category_id': category_id,
                'supplier_id': supplier_id,
                'include_inactive': include_inactive
            },
            'generated_at': datetime.now(),
            'summary': summary,
            'data': product_data
        }
    
    # ==================== EXCEL EXPORT ====================
    
    def export_to_excel(
        self,
        report_type: str,
        data: List[Dict[str, Any]],
        summary: Dict[str, Any],
        include_charts: bool = False
    ) -> bytes:
        """
        Export report data to Excel format
        """
        # Create DataFrame from data
        df = pd.DataFrame(data)
        
        # Create Excel writer
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Write main data sheet
            df.to_excel(writer, sheet_name='Report Data', index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Report Data']
            for i, col in enumerate(df.columns):
                column_len = max(df[col].astype(str).str.len().max(), len(str(col))) + 2
                worksheet.set_column(i, i, column_len)
            
            # Write summary sheet
            summary_df = pd.DataFrame([summary])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Add charts if requested
            if include_charts and not df.empty:
                self._add_excel_charts(writer, df, report_type)
        
        return output.getvalue()
    
    def _add_excel_charts(self, writer, df: pd.DataFrame, report_type: str):
        """Add charts to Excel file"""
        workbook = writer.book
        
        if report_type == 'sales':
            if 'period' in df.columns and 'total_revenue' in df.columns:
                chart_sheet = workbook.add_worksheet('Charts')
                
                # Create a bar chart
                chart = workbook.add_chart({'type': 'column'})
                
                # Configure the chart
                chart.add_series({
                    'name': 'Revenue',
                    'categories': ['Report Data', 1, 0, len(df), 0],
                    'values': ['Report Data', 1, df.columns.get_loc('total_revenue'), len(df), df.columns.get_loc('total_revenue')],
                })
                
                chart.set_title({'name': f'Sales Revenue by Period'})
                chart.set_x_axis({'name': 'Period'})
                chart.set_y_axis({'name': 'Revenue ($)'})
                
                # Insert chart
                chart_sheet.insert_chart('A1', chart)
        
        elif report_type == 'inventory':
            if 'stock_status' in df.columns:
                # Count by stock status
                status_counts = df['stock_status'].value_counts()
                status_df = pd.DataFrame({
                    'Status': status_counts.index,
                    'Count': status_counts.values
                })
                
                # Write status data
                status_df.to_excel(writer, sheet_name='Status Summary', index=False)
                
                # Create pie chart
                chart_sheet = workbook.add_worksheet('Charts')
                chart = workbook.add_chart({'type': 'pie'})
                
                chart.add_series({
                    'name': 'Stock Status',
                    'categories': ['Status Summary', 1, 0, len(status_df), 0],
                    'values': ['Status Summary', 1, 1, len(status_df), 1],
                })
                
                chart.set_title({'name': 'Inventory Stock Status Distribution'})
                chart_sheet.insert_chart('A1', chart)
    
    # ==================== QUICK REPORTS ====================
    
    def quick_sales_summary(self, days: int = 30) -> Dict[str, Any]:
        """Quick sales summary for dashboard"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Total sales
        total_sales = self.db.query(func.count(Sale.id)).filter(
            and_(
                Sale.status == "completed",
                func.date(Sale.sale_date) >= start_date,
                func.date(Sale.sale_date) <= end_date
            )
        ).scalar() or 0
        
        # Total revenue
        total_revenue_result = self.db.query(func.sum(Sale.grand_total)).filter(
            and_(
                Sale.status == "completed",
                func.date(Sale.sale_date) >= start_date,
                func.date(Sale.sale_date) <= end_date
            )
        ).first()
        total_revenue = total_revenue_result[0] or Decimal('0.00')
        
        # Average order value
        avg_order_value = total_revenue / total_sales if total_sales > 0 else Decimal('0.00')
        
        # Top products
        top_products = self.db.query(
            SaleItem.product_name,
            func.sum(SaleItem.quantity).label('total_quantity')
        ).join(Sale).filter(
            and_(
                Sale.status == "completed",
                func.date(Sale.sale_date) >= start_date,
                func.date(Sale.sale_date) <= end_date
            )
        ).group_by(SaleItem.product_name).order_by(
            func.sum(SaleItem.quantity).desc()
        ).limit(5).all()
        
        # Daily trend (last 7 days)
        daily_trend = []
        for i in range(7, 0, -1):
            day_date = end_date - timedelta(days=i)
            day_sales = self.db.query(func.count(Sale.id)).filter(
                and_(
                    Sale.status == "completed",
                    func.date(Sale.sale_date) == day_date
                )
            ).scalar() or 0
            
            daily_trend.append({
                'date': day_date,
                'sales': day_sales
            })
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': days
            },
            'total_sales': total_sales,
            'total_revenue': float(total_revenue),
            'avg_order_value': float(avg_order_value),
            'top_products': [
                {'product': p.product_name, 'quantity': p.total_quantity}
                for p in top_products
            ],
            'daily_trend': daily_trend
        }
    
    def quick_inventory_summary(self) -> Dict[str, Any]:
        """Quick inventory summary for dashboard"""
        # Total products
        total_products = self.db.query(func.count(Product.id)).filter(
            Product.is_active == True
        ).scalar() or 0
        
        # Total stock value
        total_stock_value_result = self.db.query(
            func.sum(Product.current_stock * Product.cost_price)
        ).filter(Product.is_active == True).first()
        total_stock_value = total_stock_value_result[0] or Decimal('0.00')
        
        # Low stock count
        low_stock_count = self.db.query(func.count(Product.id)).filter(
            and_(
                Product.current_stock <= Product.min_stock_level,
                Product.is_active == True
            )
        ).scalar() or 0
        
        # Out of stock count
        out_of_stock_count = self.db.query(func.count(Product.id)).filter(
            and_(
                Product.current_stock == 0,
                Product.is_active == True
            )
        ).scalar() or 0
        
        # Category distribution
        category_distribution = self.db.query(
            Category.name,
            func.count(Product.id).label('product_count')
        ).join(Product, isouter=True).group_by(Category.name).all()
        
        return {
            'total_products': total_products,
            'total_stock_value': float(total_stock_value),
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'category_distribution': [
                {'category': c.name, 'count': c.product_count}
                for c in category_distribution
            ]
        }