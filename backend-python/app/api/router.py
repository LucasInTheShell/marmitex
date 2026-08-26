from fastapi import APIRouter

from app.modules.auth.api.router import router as auth_router
from app.modules.companies.api.router import router as companies_router
from app.modules.menus.api.router import router as menus_router
from app.modules.orders.api.router import router as orders_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(companies_router)
api_router.include_router(menus_router)
api_router.include_router(orders_router)

