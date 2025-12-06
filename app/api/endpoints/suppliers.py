# app/api/endpoints/suppliers.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.database import get_db
from app.schemas.supplier import Supplier, SupplierCreate, SupplierUpdate
from app.crud.supplier import supplier as supplier_crud
from app.dependencies.auth import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("/", response_model=List[Supplier])
def read_suppliers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(False, description="Show only active suppliers"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve all suppliers with pagination.
    Optionally filter by active status.
    """
    if active_only:
        return supplier_crud.get_active_suppliers(db, skip=skip, limit=limit)
    return supplier_crud.get_all(db, skip=skip, limit=limit)


@router.get("/search", response_model=List[Supplier])
def search_suppliers(
    search_term: str = Query(..., min_length=1, description="Search term for name, contact, email, or phone"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Search suppliers by name, contact person, email, or phone.
    """
    return supplier_crud.search(db, search_term, skip=skip, limit=limit)


@router.get("/{supplier_id}", response_model=Supplier)
def read_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve a specific supplier by ID.
    """
    db_supplier = supplier_crud.get(db, supplier_id)
    if db_supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    return db_supplier


@router.post("/", response_model=Supplier, status_code=status.HTTP_201_CREATED)
def create_supplier(
    supplier: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new supplier.
    """
    # Check if supplier with same name exists
    existing_supplier = supplier_crud.get_by_name(db, supplier.name)
    if existing_supplier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supplier with this name already exists"
        )
    
    # Check if email is unique (if provided)
    if supplier.email:
        existing_email = supplier_crud.get_by_email(db, supplier.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supplier with this email already exists"
            )
    
    return supplier_crud.create(db, supplier)


@router.put("/{supplier_id}", response_model=Supplier)
def update_supplier(
    supplier_id: int,
    supplier: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a supplier.
    """
    db_supplier = supplier_crud.update(db, supplier_id, supplier)
    if db_supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    return db_supplier


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a supplier.
    """
    success = supplier_crud.delete(db, supplier_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    return None