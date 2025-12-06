# app/api/endpoints/categories.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from app.database.database import get_db
from app.schemas.category import Category, CategoryCreate, CategoryUpdate
from app.crud.category import category as category_crud
from app.dependencies.auth import get_current_active_user, get_current_admin
from app.models.user import User

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=List[Category])
def read_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve all categories with pagination.
    """
    categories = category_crud.get_all(db, skip=skip, limit=limit)
    return categories


@router.get("/{category_id}", response_model=Category)
def read_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve a specific category by ID.
    """
    db_category = category_crud.get(db, category_id)
    if db_category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return db_category


@router.post("/", response_model=Category, status_code=status.HTTP_201_CREATED)
def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new category.
    """
    # Check if category with same name exists
    existing_category = category_crud.get_by_name(db, category.name)
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists"
        )
    
    return category_crud.create(db, category)


@router.put("/{category_id}", response_model=Category)
def update_category(
    category_id: int,
    category: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a category.
    """
    db_category = category_crud.update(db, category_id, category)
    if db_category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return db_category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a category.
    """
    success = category_crud.delete(db, category_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return None