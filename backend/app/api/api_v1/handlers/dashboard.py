# backend/app/api/api_v1/handlers/dashboard.py
from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Dict, List, Any
from datetime import date, datetime, timedelta
from app.services.dashboard_service import DashboardService
from app.api.deps.user_deps import get_current_user
from app.models.user_model import User
import logging

logger = logging.getLogger(__name__)
dashboard_router = APIRouter()

@dashboard_router.get("/overview", summary="Get dashboard overview")
async def get_dashboard_overview(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    try:
        overview = await DashboardService.get_overview()
        return overview
    except Exception as e:
        logger.error(f"Error getting dashboard overview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dashboard overview"
        )

@dashboard_router.get("/stats", summary="Get dashboard statistics")
async def get_dashboard_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days for statistics"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    try:
        stats = await DashboardService.get_statistics(days)
        return stats
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dashboard statistics"
        )

@dashboard_router.get("/recent-transactions", summary="Get recent transactions")
async def get_recent_transactions(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    try:
        transactions = await DashboardService.get_recent_transactions(limit)
        return transactions
    except Exception as e:
        logger.error(f"Error getting recent transactions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recent transactions"
        )

@dashboard_router.get("/due-items", summary="Get items due for payment")
async def get_due_items(
    days_ahead: int = Query(7, ge=1, le=30, description="Look ahead days"),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    try:
        due_items = await DashboardService.get_due_items(days_ahead)
        return due_items
    except Exception as e:
        logger.error(f"Error getting due items: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get due items"
        )

@dashboard_router.get("/overdue-items", summary="Get overdue items")
async def get_overdue_items(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    try:
        overdue_items = await DashboardService.get_overdue_items()
        return overdue_items
    except Exception as e:
        logger.error(f"Error getting overdue items: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get overdue items"
        )

@dashboard_router.get("/performance", summary="Get performance metrics")
async def get_performance_metrics(
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    try:
        metrics = await DashboardService.get_performance_metrics(start_date, end_date)
        return metrics
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get performance metrics"
        )