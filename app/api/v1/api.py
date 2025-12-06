# app/api/v1/api.py
from fastapi import APIRouter
from app.api.endpoints import categories, suppliers, products, auth, users, sales, reports  # Added reports

api_router = APIRouter()
api_router.include_router(categories.router)
api_router.include_router(suppliers.router)
api_router.include_router(products.router)
api_router.include_router(sales.router)
api_router.include_router(reports.router)  # Added this line
api_router.include_router(auth.router)
api_router.include_router(users.router)