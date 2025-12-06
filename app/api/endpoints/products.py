# app/api/endpoints/products.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.database.database import get_db
from app.schemas.product import (
    Product, ProductCreate, ProductUpdate, 
    ProductStockUpdate, ProductWithRelations
)
from app.crud.product import product as product_crud
from app.crud.category import category as category_crud
from app.crud.supplier import supplier as supplier_crud
from app.dependencies.auth import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=List[Product])
def read_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    active_only: bool = Query(True, description="Show only active products"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve all products with filtering options.
    """
    products = product_crud.get_all(
        db, skip=skip, limit=limit,
        category_id=category_id,
        supplier_id=supplier_id,
        active_only=active_only
    )
    
    # Add category and supplier names to response
    enhanced_products = []
    for prod in products:
        product_dict = {c.name: getattr(prod, c.name) for c in prod.__table__.columns}
        
        if prod.category:
            product_dict['category_name'] = prod.category.name
        
        if prod.supplier:
            product_dict['supplier_name'] = prod.supplier.name
        
        enhanced_products.append(product_dict)
    
    return enhanced_products


@router.get("/search", response_model=List[Product])
def search_products(
    search_term: str = Query(..., min_length=1, description="Search term for name, SKU, barcode, brand, or description"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Search products by various fields.
    """
    return product_crud.search(db, search_term, skip=skip, limit=limit)


@router.get("/low-stock", response_model=List[Product])
def get_low_stock_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get products with stock levels at or below minimum threshold.
    """
    return product_crud.get_low_stock(db, skip=skip, limit=limit)


@router.get("/out-of-stock", response_model=List[Product])
def get_out_of_stock_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get products that are out of stock.
    """
    return product_crud.get_out_of_stock(db, skip=skip, limit=limit)


@router.get("/{product_id}", response_model=ProductWithRelations)
def read_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve a specific product by ID with full details.
    """
    db_product = product_crud.get(db, product_id)
    if db_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Get related data
    product_data = {c.name: getattr(db_product, c.name) for c in db_product.__table__.columns}
    
    if db_product.category:
        product_data['category'] = {
            'id': db_product.category.id,
            'name': db_product.category.name,
            'description': db_product.category.description
        }
    
    if db_product.supplier:
        product_data['supplier'] = {
            'id': db_product.supplier.id,
            'name': db_product.supplier.name,
            'contact_person': db_product.supplier.contact_person,
            'email': db_product.supplier.email
        }
    
    return product_data


@router.get("/sku/{sku}", response_model=Product)
def read_product_by_sku(
    sku: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve a product by SKU.
    """
    db_product = product_crud.get_by_sku(db, sku)
    if db_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return db_product


@router.get("/barcode/{barcode}", response_model=Product)
def read_product_by_barcode(
    barcode: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve a product by barcode.
    """
    db_product = product_crud.get_by_barcode(db, barcode)
    if db_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return db_product


@router.post("/", response_model=Product, status_code=status.HTTP_201_CREATED)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new product.
    """
    # Check if SKU already exists
    existing_product = product_crud.get_by_sku(db, product.sku)
    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product with this SKU already exists"
        )
    
    # Check if barcode already exists (if provided)
    if product.barcode:
        existing_barcode = product_crud.get_by_barcode(db, product.barcode)
        if existing_barcode:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product with this barcode already exists"
            )
    
    # Verify category exists (if provided)
    if product.category_id:
        db_category = category_crud.get(db, product.category_id)
        if not db_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found"
            )
    
    # Verify supplier exists (if provided)
    if product.supplier_id:
        db_supplier = supplier_crud.get(db, product.supplier_id)
        if not db_supplier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supplier not found"
            )
    
    return product_crud.create(db, product)


@router.put("/{product_id}", response_model=Product)
def update_product(
    product_id: int,
    product: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a product.
    """
    db_product = product_crud.update(db, product_id, product)
    if db_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return db_product


@router.patch("/{product_id}/stock", response_model=Product)
def update_product_stock(
    product_id: int,
    stock_update: ProductStockUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update product stock (add or remove quantity).
    """
    db_product = product_crud.update_stock(db, product_id, stock_update)
    if db_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or insufficient stock"
        )
    return db_product


@router.post("/bulk-stock-update")
def bulk_update_stock(
    stock_updates: Dict[int, int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Bulk update stock for multiple products.
    Format: {product_id: quantity_change}
    """
    results = product_crud.bulk_update_stock(db, stock_updates)
    
    failed_updates = {pid: success for pid, success in results.items() if not success}
    if failed_updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update stock for products: {list(failed_updates.keys())}"
        )
    
    return {"message": "Stock updated successfully", "updated_products": len(results)}


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete (deactivate) a product.
    """
    success = product_crud.delete(db, product_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return None


@router.get("/inventory/summary")
def get_inventory_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get inventory summary statistics.
    """
    summary = product_crud.get_inventory_summary(db)
    return summary




# Add these endpoints AFTER the existing endpoints but BEFORE the router ends

@router.get("/category/{category_name}", response_model=List[ProductWithRelations])
def get_products_by_category_name(
    category_name: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all products under a specific category by category name.
    Example: /api/v1/products/category/Electronics
    """
    products = product_crud.get_products_by_category_name(
        db, 
        category_name=category_name,
        skip=skip, 
        limit=limit
    )
    
    # Enhance response with full category and supplier details
    enhanced_products = []
    for product in products:
        product_data = {c.name: getattr(product, c.name) for c in product.__table__.columns}
        
        # Add full category details
        if product.category:
            product_data['category'] = {
                'id': product.category.id,
                'name': product.category.name,
                'description': product.category.description,
                'created_at': product.category.created_at,
                'updated_at': product.category.updated_at
            }
            product_data['category_name'] = product.category.name
        
        # Add full supplier details
        if product.supplier:
            product_data['supplier'] = {
                'id': product.supplier.id,
                'name': product.supplier.name,
                'contact_person': product.supplier.contact_person,
                'email': product.supplier.email,
                'phone': product.supplier.phone,
                'address': product.supplier.address,
                'city': product.supplier.city,
                'state': product.supplier.state,
                'country': product.supplier.country,
                'postal_code': product.supplier.postal_code,
                'tax_id': product.supplier.tax_id,
                'website': product.supplier.website,
                'is_active': product.supplier.is_active,
                'payment_terms': product.supplier.payment_terms,
                'rating': product.supplier.rating,
                'notes': product.supplier.notes,
                'created_at': product.supplier.created_at,
                'updated_at': product.supplier.updated_at
            }
            product_data['supplier_name'] = product.supplier.name
        
        enhanced_products.append(product_data)
    
    return enhanced_products


@router.get("/supplier/{supplier_name}", response_model=List[ProductWithRelations])
def get_products_by_supplier_name(
    supplier_name: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all products from a specific supplier by supplier name.
    Example: /api/v1/products/supplier/Amazon
    """
    products = product_crud.get_products_by_supplier_name(
        db, 
        supplier_name=supplier_name,
        skip=skip, 
        limit=limit
    )
    
    # Enhance response with full category and supplier details
    enhanced_products = []
    for product in products:
        product_data = {c.name: getattr(product, c.name) for c in product.__table__.columns}
        
        # Add full category details
        if product.category:
            product_data['category'] = {
                'id': product.category.id,
                'name': product.category.name,
                'description': product.category.description,
                'created_at': product.category.created_at,
                'updated_at': product.category.updated_at
            }
            product_data['category_name'] = product.category.name
        
        # Add full supplier details
        if product.supplier:
            product_data['supplier'] = {
                'id': product.supplier.id,
                'name': product.supplier.name,
                'contact_person': product.supplier.contact_person,
                'email': product.supplier.email,
                'phone': product.supplier.phone,
                'address': product.supplier.address,
                'city': product.supplier.city,
                'state': product.supplier.state,
                'country': product.supplier.country,
                'postal_code': product.supplier.postal_code,
                'tax_id': product.supplier.tax_id,
                'website': product.supplier.website,
                'is_active': product.supplier.is_active,
                'payment_terms': product.supplier.payment_terms,
                'rating': product.supplier.rating,
                'notes': product.supplier.notes,
                'created_at': product.supplier.created_at,
                'updated_at': product.supplier.updated_at
            }
            product_data['supplier_name'] = product.supplier.name
        
        enhanced_products.append(product_data)
    
    return enhanced_products


@router.get("/with-details", response_model=List[ProductWithRelations])
def get_all_products_with_details(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    supplier_id: Optional[int] = Query(None, description="Filter by supplier ID"),
    active_only: bool = Query(True, description="Show only active products"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all products with full category and supplier details.
    Returns all columns from product, category, and supplier tables.
    """
    products = product_crud.get_all_products_with_relations(
        db, 
        skip=skip, 
        limit=limit,
        category_id=category_id,
        supplier_id=supplier_id,
        active_only=active_only
    )
    
    # Enhance response with full category and supplier details
    enhanced_products = []
    for product in products:
        product_data = {c.name: getattr(product, c.name) for c in product.__table__.columns}
        
        # Add full category details
        if product.category:
            product_data['category'] = {
                'id': product.category.id,
                'name': product.category.name,
                'description': product.category.description,
                'created_at': product.category.created_at,
                'updated_at': product.category.updated_at
            }
            product_data['category_name'] = product.category.name
        
        # Add full supplier details
        if product.supplier:
            product_data['supplier'] = {
                'id': product.supplier.id,
                'name': product.supplier.name,
                'contact_person': product.supplier.contact_person,
                'email': product.supplier.email,
                'phone': product.supplier.phone,
                'address': product.supplier.address,
                'city': product.supplier.city,
                'state': product.supplier.state,
                'country': product.supplier.country,
                'postal_code': product.supplier.postal_code,
                'tax_id': product.supplier.tax_id,
                'website': product.supplier.website,
                'is_active': product.supplier.is_active,
                'payment_terms': product.supplier.payment_terms,
                'rating': product.supplier.rating,
                'notes': product.supplier.notes,
                'created_at': product.supplier.created_at,
                'updated_at': product.supplier.updated_at
            }
            product_data['supplier_name'] = product.supplier.name
        
        enhanced_products.append(product_data)
    
    return enhanced_products