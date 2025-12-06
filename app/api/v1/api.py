# app/api/v1/api.py
from fastapi import APIRouter
from app.api.endpoints import categories

api_router = APIRouter()
api_router.include_router(categories.router)