from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
import os
import json
import httpx

from app.core.config import settings
from app.database.database import engine, Base
from app.api.v1.api import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up...")
    print(f"API Documentation: http://localhost:8000/docs")
    print(f"Admin Dashboard: http://localhost:8000/dashboard")
    
    # Create tables (in production, use Alembic migrations instead)
    Base.metadata.create_all(bind=engine)
    
    yield
    
    # Shutdown
    print("Shutting down...")

# Create FastAPI app
app = FastAPI(
    title="Inventory Management System",
    description="REST API + Admin Dashboard for managing inventory items",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, you can change this later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
# app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup Jinja2 templates for frontend
templates = Jinja2Templates(directory="app/templates")

# Include API router
app.include_router(api_router, prefix="/api/v1")

# ==================== FRONTEND ROUTES ====================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page - redirects to login"""
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Register page"""
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/products", response_class=HTMLResponse)
async def products_page(request: Request):
    """Products management page"""
    return templates.TemplateResponse("products.html", {"request": request})

@app.get("/products/create", response_class=HTMLResponse)
async def create_product_page(request: Request):
    """Create product page"""
    return templates.TemplateResponse("products_create.html", {"request": request})

@app.get("/products/edit/{product_id}", response_class=HTMLResponse)
async def edit_product_page(request: Request, product_id: int):
    """Edit product page"""
    return templates.TemplateResponse("products_edit.html", {"request": request, "product_id": product_id})

@app.get("/categories", response_class=HTMLResponse)
async def categories_page(request: Request):
    """Categories management page"""
    return templates.TemplateResponse("categories.html", {"request": request})

@app.get("/suppliers", response_class=HTMLResponse)
async def suppliers_page(request: Request):
    """Suppliers management page"""
    return templates.TemplateResponse("suppliers.html", {"request": request})

@app.get("/sales", response_class=HTMLResponse)
async def sales_page(request: Request):
    """Sales management page"""
    return templates.TemplateResponse("sales.html", {"request": request})

@app.get("/sales/create", response_class=HTMLResponse)
async def create_sale_page(request: Request):
    """Create sale page"""
    return templates.TemplateResponse("sales_create.html", {"request": request})

@app.get("/reports/sales", response_class=HTMLResponse)
async def sales_report_page(request: Request):
    """Sales report page"""
    return templates.TemplateResponse("reports_sales.html", {"request": request})

@app.get("/reports/inventory", response_class=HTMLResponse)
async def inventory_report_page(request: Request):
    """Inventory report page"""
    return templates.TemplateResponse("reports_inventory.html", {"request": request})

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """User profile page"""
    return templates.TemplateResponse("profile.html", {"request": request})

@app.get("/logout")
async def logout():
    """Logout endpoint - clears token"""
    response = RedirectResponse(url="/login")
    response.delete_cookie(key="access_token")
    return response

# ==================== HEALTH & INFO ENDPOINTS ====================

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "inventory-system"}

@app.get("/info")
def app_info():
    return {
        "name": "Inventory Management System",
        "version": "1.0.0",
        "api_version": "v1",
        "api_endpoints": "/api/v1",
        "admin_dashboard": "/dashboard",
        "docs": "/docs",
        "redoc": "/redoc"
    }

# ==================== ERROR HANDLERS ====================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors"""
    if request.url.path.startswith('/api/'):
        return JSONResponse(
            status_code=404,
            content={"detail": "API endpoint not found"}
        )
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    """Handle 500 errors"""
    if request.url.path.startswith('/api/'):
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)

# ==================== BACKWARD COMPATIBILITY ====================

@app.get("/api/v1")
def api_root():
    """API root endpoint"""
    return {
        "message": "Inventory Management System API v1",
        "endpoints": {
            "auth": "/api/v1/auth",
            "products": "/api/v1/products",
            "categories": "/api/v1/categories",
            "suppliers": "/api/v1/suppliers",
            "sales": "/api/v1/sales",
            "reports": "/api/v1/reports"
        },
        "documentation": "/docs",
        "admin_dashboard": "/dashboard"
    }

@app.get("/docs", include_in_schema=False)
async def custom_docs():
    """Redirect to Swagger UI"""
    return RedirectResponse(url="/docs")

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )