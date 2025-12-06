# app/schemas/report.py
from pydantic import BaseModel, ConfigDict
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal


class ReportBase(BaseModel):
    name: str
    description: Optional[str] = None
    report_type: str  # sales, inventory, product, supplier, etc.
    format: str = "json"  # json, excel, pdf
    filters: Optional[Dict[str, Any]] = None


class ReportCreate(ReportBase):
    pass


class Report(ReportBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    generated_at: datetime
    generated_by: Optional[int] = None
    file_path: Optional[str] = None
    download_url: Optional[str] = None


class SalesReportRequest(BaseModel):
    start_date: date
    end_date: date
    group_by: str = "day"  # day, week, month, product, category, supplier
    include_details: bool = False
    format: str = "json"  # json, excel


class SalesReportResponse(BaseModel):
    report_date: datetime
    period: Dict[str, date]
    summary: Dict[str, Any]
    data: List[Dict[str, Any]]
    total_sales: int
    total_revenue: Decimal
    total_products_sold: int
    average_order_value: Decimal


class InventoryReportRequest(BaseModel):
    report_type: str = "stock_summary"  # stock_summary, low_stock, out_of_stock, slow_moving
    threshold: Optional[int] = None
    format: str = "json"


class InventoryReportResponse(BaseModel):
    report_date: datetime
    report_type: str
    summary: Dict[str, Any]
    data: List[Dict[str, Any]]
    total_products: int
    total_stock_value: Decimal
    low_stock_count: int
    out_of_stock_count: int


class ProductReportRequest(BaseModel):
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None
    include_inactive: bool = False
    format: str = "json"


class ProductReportResponse(BaseModel):
    report_date: datetime
    filters: Dict[str, Any]
    summary: Dict[str, Any]
    data: List[Dict[str, Any]]
    total_products: int
    average_price: Decimal
    total_stock_value: Decimal


class ExportRequest(BaseModel):
    report_type: str
    format: str = "excel"  # excel, csv
    include_charts: bool = False
    filters: Optional[Dict[str, Any]] = None