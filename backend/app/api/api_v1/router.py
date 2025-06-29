# backend/app/api/api_v1/router.py
from fastapi import APIRouter
from app.api.api_v1.handlers import user, customer, item, transaction, dashboard, reports
from app.api.auth.jwt import auth_router

router = APIRouter()

# Authentication
router.include_router(auth_router, prefix="/auth", tags=["auth"])

# Core entities
router.include_router(user.user_router, prefix="/users", tags=["users"])
router.include_router(customer.customer_router, prefix="/customers", tags=["customers"])
router.include_router(item.item_router, prefix="/items", tags=["items"])
router.include_router(transaction.transaction_router, prefix="/transactions", tags=["transactions"])

# Dashboard and reporting
router.include_router(dashboard.dashboard_router, prefix="/dashboard", tags=["dashboard"])
router.include_router(reports.reports_router, prefix="/reports", tags=["reports"])