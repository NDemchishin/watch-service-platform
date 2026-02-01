"""
API endpoints.
"""
from fastapi import APIRouter

from app.api import employees, receipts, operations, polishing, returns, history

# Главный роутер API
api_router = APIRouter(prefix="/api/v1")

# Подключаем все модули
api_router.include_router(employees.router)
api_router.include_router(receipts.router)
api_router.include_router(operations.router)
api_router.include_router(polishing.router)
api_router.include_router(returns.router)
api_router.include_router(history.router)

__all__ = ["api_router"]
