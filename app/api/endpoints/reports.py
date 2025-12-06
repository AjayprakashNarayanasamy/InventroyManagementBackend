# app/api/endpoints/reports.py
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime, timedelta
import io

from app.database.database import get_db
from app.schemas.report import (
    SalesReportRequest, SalesReportResponse,
    InventoryReportRequest, InventoryReportResponse,
    ProductReportRequest, ProductReportResponse,
    ExportRequest
)
from app.models.report import ReportService
from app.dependencies.auth import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])


# ==================== SALES REPORTS ====================

@router.post("/sales", response_model=SalesReportResponse)
def generate_sales_report(
    request: SalesReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate sales report for a specific period.
    Can group by day, week, month, or product.
    """
    report_service = ReportService(db)
    
    result = report_service.generate_sales_report(
        start_date=request.start_date,
        end_date=request.end_date,
        group_by=request.group_by
    )
    
    # Calculate additional metrics
    data = result.get('data', [])
    total_revenue = sum(item.get('total_revenue', 0) for item in data)
    total_sales = sum(item.get('sales_count', 0) for item in data)
    total_products_sold = result.get('total_products_sold', 0)
    
    avg_order_value = total_revenue / total_sales if total_sales > 0 else 0
    
    # If Excel format requested
    if request.format == "excel":
        excel_data = report_service.export_to_excel(
            report_type="sales",
            data=data,
            summary=result.get('summary', {})
        )
        
        # Return as downloadable file
        return StreamingResponse(
            io.BytesIO(excel_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=sales_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            }
        )
    
    return {
        "report_date": datetime.now(),
        "period": result.get('period', {}),
        "summary": result.get('summary', {}),
        "data": data,
        "total_sales": total_sales,
        "total_revenue": total_revenue,
        "total_products_sold": total_products_sold,
        "average_order_value": avg_order_value
    }


@router.get("/sales/daily")
def get_daily_sales_report(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get daily sales report for the last N days.
    """
    report_service = ReportService(db)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    result = report_service.generate_sales_report(
        start_date=start_date,
        end_date=end_date,
        group_by="day"
    )
    
    return result


@router.get("/sales/top-products")
def get_top_products_report(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    limit: int = Query(10, ge=1, le=100, description="Number of top products to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get top selling products report.
    """
    report_service = ReportService(db)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    result = report_service.generate_sales_report(
        start_date=start_date,
        end_date=end_date,
        group_by="product"
    )
    
    # Limit the number of products if requested
    data = result.get('data', [])
    if limit < len(data):
        result['data'] = data[:limit]
    
    return result


# ==================== INVENTORY REPORTS ====================

@router.post("/inventory", response_model=InventoryReportResponse)
def generate_inventory_report(
    request: InventoryReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate inventory report.
    Types: stock_summary, low_stock, out_of_stock, slow_moving
    """
    report_service = ReportService(db)
    
    result = report_service.generate_inventory_report(
        report_type=request.report_type,
        threshold=request.threshold
    )
    
    # If Excel format requested
    if request.format == "excel":
        excel_data = report_service.export_to_excel(
            report_type="inventory",
            data=result.get('data', []),
            summary=result.get('summary', {})
        )
        
        return StreamingResponse(
            io.BytesIO(excel_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=inventory_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            }
        )
    
    return {
        "report_date": result.get('generated_at', datetime.now()),
        "report_type": result.get('report_type', ''),
        "summary": result.get('summary', {}),
        "data": result.get('data', []),
        "total_products": result.get('summary', {}).get('total_products', 0),
        "total_stock_value": result.get('summary', {}).get('total_stock_value', 0),
        "low_stock_count": result.get('summary', {}).get('low_stock_count', 0),
        "out_of_stock_count": result.get('summary', {}).get('out_of_stock_count', 0)
    }


@router.get("/inventory/low-stock")
def get_low_stock_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get low stock inventory report.
    """
    report_service = ReportService(db)
    result = report_service.generate_inventory_report(report_type="low_stock")
    
    return {
        "report_date": datetime.now(),
        "report_type": "low_stock",
        "data": result.get('data', []),
        "summary": result.get('summary', {})
    }


@router.get("/inventory/out-of-stock")
def get_out_of_stock_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get out of stock inventory report.
    """
    report_service = ReportService(db)
    result = report_service.generate_inventory_report(report_type="out_of_stock")
    
    return {
        "report_date": datetime.now(),
        "report_type": "out_of_stock",
        "data": result.get('data', []),
        "summary": result.get('summary', {})
    }


# ==================== PRODUCT REPORTS ====================

@router.post("/products", response_model=ProductReportResponse)
def generate_product_report(
    request: ProductReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate product report with filtering options.
    """
    report_service = ReportService(db)
    
    result = report_service.generate_product_report(
        category_id=request.category_id,
        supplier_id=request.supplier_id,
        include_inactive=request.include_inactive
    )
    
    # If Excel format requested
    if request.format == "excel":
        excel_data = report_service.export_to_excel(
            report_type="product",
            data=result.get('data', []),
            summary=result.get('summary', {})
        )
        
        return StreamingResponse(
            io.BytesIO(excel_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=product_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            }
        )
    
    data = result.get('data', [])
    summary = result.get('summary', {})
    
    # Calculate average price
    avg_price = 0
    if data and 'selling_price' in data[0]:
        avg_price = sum(item.get('selling_price', 0) for item in data) / len(data)
    
    return {
        "report_date": result.get('generated_at', datetime.now()),
        "filters": result.get('filters', {}),
        "summary": summary,
        "data": data,
        "total_products": summary.get('total_products', 0),
        "average_price": avg_price,
        "total_stock_value": summary.get('total_stock_value', 0)
    }


# ==================== DASHBOARD REPORTS ====================

@router.get("/dashboard/sales-summary")
def get_dashboard_sales_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get quick sales summary for dashboard.
    """
    report_service = ReportService(db)
    result = report_service.quick_sales_summary(days=days)
    
    return result


@router.get("/dashboard/inventory-summary")
def get_dashboard_inventory_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get quick inventory summary for dashboard.
    """
    report_service = ReportService(db)
    result = report_service.quick_inventory_summary()
    
    return result


# ==================== EXPORT ENDPOINTS ====================

@router.post("/export")
def export_report(
    request: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Export report in various formats (Excel, CSV).
    """
    report_service = ReportService(db)
    
    # Generate appropriate report based on type
    if request.report_type.startswith("sales"):
        # Parse date range from filters
        start_date = request.filters.get('start_date', date.today() - timedelta(days=30))
        end_date = request.filters.get('end_date', date.today())
        group_by = request.filters.get('group_by', 'day')
        
        result = report_service.generate_sales_report(
            start_date=start_date,
            end_date=end_date,
            group_by=group_by
        )
        data = result.get('data', [])
        summary = result.get('summary', {})
        
    elif request.report_type.startswith("inventory"):
        report_type = request.filters.get('report_type', 'stock_summary')
        threshold = request.filters.get('threshold')
        
        result = report_service.generate_inventory_report(
            report_type=report_type,
            threshold=threshold
        )
        data = result.get('data', [])
        summary = result.get('summary', {})
        
    elif request.report_type.startswith("product"):
        category_id = request.filters.get('category_id')
        supplier_id = request.filters.get('supplier_id')
        include_inactive = request.filters.get('include_inactive', False)
        
        result = report_service.generate_product_report(
            category_id=category_id,
            supplier_id=supplier_id,
            include_inactive=include_inactive
        )
        data = result.get('data', [])
        summary = result.get('summary', {})
        
    else:
        raise HTTPException(status_code=400, detail="Invalid report type")
    
    # Export based on format
    if request.format == "excel":
        excel_data = report_service.export_to_excel(
            report_type=request.report_type,
            data=data,
            summary=summary,
            include_charts=request.include_charts
        )
        
        filename = f"{request.report_type}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(excel_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    elif request.format == "csv":
        # Convert to CSV
        import pandas as pd
        df = pd.DataFrame(data)
        csv_data = df.to_csv(index=False)
        
        filename = f"{request.report_type}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")


# ==================== QUICK REPORTS ====================

@router.get("/quick/monthly-sales")
def get_monthly_sales_report(
    months: int = Query(6, ge=1, le=24, description="Number of months to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get monthly sales report for the last N months.
    """
    report_service = ReportService(db)
    end_date = datetime.now().date()
    start_date = date(end_date.year, end_date.month, 1) - timedelta(days=30*months)
    
    result = report_service.generate_sales_report(
        start_date=start_date,
        end_date=end_date,
        group_by="month"
    )
    
    return result


@router.get("/quick/category-performance")
def get_category_performance_report(
    days: int = Query(90, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get sales performance by category.
    """
    # This would require joining sales with products and categories
    # For now, return a simplified version
    return {"message": "Category performance report endpoint", "days": days}