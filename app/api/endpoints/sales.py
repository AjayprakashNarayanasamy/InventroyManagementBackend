# app/api/endpoints/sales.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.database.database import get_db
from app.schemas.sale import Sale, SaleCreate, SaleUpdate, SaleWithItems, SaleSummary, DailySales
from app.crud.sale import sale as sale_crud
from app.crud.product import product as product_crud
from app.dependencies.auth import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/sales", tags=["sales"])


@router.get("/", response_model=List[Sale])
def read_sales(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="Filter by sale status"),
    payment_status: Optional[str] = Query(None, description="Filter by payment status"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve all sales with filtering options.
    """
    sales = sale_crud.get_all(
        db, skip=skip, limit=limit,
        status=status,
        payment_status=payment_status,
        start_date=start_date,
        end_date=end_date
    )
    
    # Add user name to response
    enhanced_sales = []
    for sale_obj in sales:
        sale_dict = {c.name: getattr(sale_obj, c.name) for c in sale_obj.__table__.columns}
        
        if sale_obj.user:
            sale_dict['user_name'] = sale_obj.user.full_name or sale_obj.user.username
        
        enhanced_sales.append(sale_dict)
    
    return enhanced_sales


@router.get("/{sale_id}", response_model=SaleWithItems)
def read_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve a specific sale by ID with all items.
    """
    db_sale = sale_crud.get(db, sale_id)
    if not db_sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sale not found"
        )
    
    # Get sale with user name
    sale_data = {c.name: getattr(db_sale, c.name) for c in db_sale.__table__.columns}
    
    if db_sale.user:
        sale_data['user_name'] = db_sale.user.full_name or db_sale.user.username
    
    # Get items
    items_data = []
    for item in db_sale.items:
        item_dict = {c.name: getattr(item, c.name) for c in item.__table__.columns}
        items_data.append(item_dict)
    
    sale_data['items'] = items_data
    
    return sale_data


@router.get("/number/{sale_number}", response_model=SaleWithItems)
def read_sale_by_number(
    sale_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve a sale by sale number.
    """
    db_sale = sale_crud.get_by_number(db, sale_number)
    if not db_sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sale not found"
        )
    
    sale_data = {c.name: getattr(db_sale, c.name) for c in db_sale.__table__.columns}
    
    if db_sale.user:
        sale_data['user_name'] = db_sale.user.full_name or db_sale.user.username
    
    items_data = []
    for item in db_sale.items:
        item_dict = {c.name: getattr(item, c.name) for c in item.__table__.columns}
        items_data.append(item_dict)
    
    sale_data['items'] = items_data
    
    return sale_data


@router.post("/", response_model=Sale, status_code=status.HTTP_201_CREATED)
def create_sale(
    sale: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new sale. This will automatically:
    1. Generate a unique sale number
    2. Validate stock availability
    3. Deduct stock from inventory
    4. Calculate totals and taxes
    """
    # Validate all products exist and have sufficient stock
    for item in sale.items:
        db_product = product_crud.get(db, item.product_id)
        if not db_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product ID {item.product_id} not found"
            )
        
        if db_product.current_stock < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for {db_product.name}. Available: {db_product.current_stock}"
            )
    
    # Create the sale
    db_sale, message = sale_crud.create(db, sale, user_id=current_user.id)
    
    if not db_sale:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Add user name to response
    sale_data = {c.name: getattr(db_sale, c.name) for c in db_sale.__table__.columns}
    sale_data['user_name'] = current_user.full_name or current_user.username
    
    return sale_data


@router.put("/{sale_id}", response_model=Sale)
def update_sale(
    sale_id: int,
    sale: SaleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a sale (only draft sales can be updated).
    """
    db_sale, message = sale_crud.update(db, sale_id, sale)
    
    if not db_sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message
        )
    
    sale_data = {c.name: getattr(db_sale, c.name) for c in db_sale.__table__.columns}
    
    if db_sale.user:
        sale_data['user_name'] = db_sale.user.full_name or db_sale.user.username
    
    return sale_data


@router.post("/{sale_id}/cancel", response_model=Sale)
def cancel_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Cancel a sale. This will:
    1. Restore stock to inventory
    2. Update sale status to cancelled
    3. Update payment status if needed
    """
    success, message = sale_crud.cancel(db, sale_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    db_sale = sale_crud.get(db, sale_id)
    sale_data = {c.name: getattr(db_sale, c.name) for c in db_sale.__table__.columns}
    
    if db_sale.user:
        sale_data['user_name'] = db_sale.user.full_name or db_sale.user.username
    
    return sale_data


@router.delete("/{sale_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a sale (only draft sales can be deleted).
    """
    success = sale_crud.delete(db, sale_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft sales can be deleted or sale not found"
        )
    return None


@router.get("/dashboard/summary", response_model=SaleSummary)
def get_sales_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get sales summary for dashboard.
    """
    summary = sale_crud.get_sales_summary(db)
    return summary


@router.get("/dashboard/daily", response_model=List[DailySales])
def get_daily_sales(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get daily sales data for charts.
    """
    daily_data = sale_crud.get_daily_sales(db, days)
    return daily_data


@router.get("/reports/by-product")
def get_sales_by_product(
    product_id: Optional[int] = Query(None, description="Filter by specific product"),
    start_date: Optional[date] = Query(None, description="Report start date"),
    end_date: Optional[date] = Query(None, description="Report end date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get sales report grouped by product.
    """
    report = sale_crud.get_sales_by_product(db, product_id, start_date, end_date)
    return {
        "report_date": datetime.now().date(),
        "filters": {
            "product_id": product_id,
            "start_date": start_date,
            "end_date": end_date
        },
        "data": report,
        "total_products": len(report),
        "total_quantity": sum(item['total_quantity'] for item in report),
        "total_revenue": sum(item['total_revenue'] for item in report)
    }


@router.get("/reports/top-products")
def get_top_products(
    limit: int = Query(10, ge=1, le=50, description="Number of top products"),
    days: int = Query(30, ge=1, le=365, description="Period in days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get top selling products.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    report = sale_crud.get_sales_by_product(db, None, start_date.date(), end_date.date())
    
    # Sort by quantity and take top N
    top_by_quantity = sorted(report, key=lambda x: x['total_quantity'], reverse=True)[:limit]
    top_by_revenue = sorted(report, key=lambda x: x['total_revenue'], reverse=True)[:limit]
    
    return {
        "period": {
            "start_date": start_date.date(),
            "end_date": end_date.date(),
            "days": days
        },
        "top_by_quantity": top_by_quantity,
        "top_by_revenue": top_by_revenue
    }