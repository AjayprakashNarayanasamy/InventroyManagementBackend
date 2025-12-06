# app/api/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from app.database.database import get_db
from app.schemas.user import User, UserCreate, UserUpdate
from app.crud.user import user as user_crud
from app.dependencies.auth import get_current_admin

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[User])
def read_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """
    Retrieve all users (admin only).
    """
    return user_crud.get_all(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=User)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """
    Retrieve a specific user by ID (admin only).
    """
    db_user = user_crud.get(db, user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return db_user


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """
    Create a new user (admin only).
    """
    existing_user = user_crud.get_by_email(db, email=user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    existing_user = user_crud.get_by_username(db, username=user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    return user_crud.create(db, user)


@router.put("/{user_id}", response_model=User)
def update_user(
    user_id: int,
    user: UserUpdate,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """
    Update a user (admin only).
    """
    db_user = user_crud.update(db, user_id, user)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return db_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """
    Delete a user (admin only).
    """
    success = user_crud.delete(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return None