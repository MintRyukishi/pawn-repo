# backend/app/api/api_v1/handlers/reports.py
from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Dict, List, Any, Optional
from datetime import date, datetime, timedelta
from app.services.reports_service import ReportsService
from app.api.deps.user_deps import get_current_user
from app.models.user_model import User
from app.models.transaction_model import TransactionType
import logging
import io

logger = logging.getLogger(__name__)
reports_router = APIRouter()

@reports_router.get("/transactions", summary="Get transaction report")
async def get_transaction_report(
    start_date: date = Query(..., description="Start date for report"),
    end_date: date = Query(..., description="End date for report"),
    transaction_type: Optional[TransactionType] = Query(None, description="Filter by transaction type"),
    format: str = Query("json", regex="^(json|csv)$", description="Report format"),
    current_user: User = Depends(get_current_user)
):
    try:
        if format == "csv":
            csv_data = await ReportsService.get_transaction_report_csv(
                start_date, end_date, transaction_type
            )
            return StreamingResponse(
                io.StringIO(csv_data),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=transactions_{start_date}_{end_date}.csv"}
            )
        else:
            report = await ReportsService.get_transaction_report(
                start_date, end_date, transaction_type
            )
            return report
    except Exception as e:
        logger.error(f"Error generating transaction report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate transaction report"
        )

@reports_router.get("/inventory", summary="Get inventory report")
async def get_inventory_report(
    format: str = Query("json", regex="^(json|csv)$", description="Report format"),
    current_user: User = Depends(get_current_user)
):
    try:
        if format == "csv":
            csv_data = await ReportsService.get_inventory_report_csv()
            return StreamingResponse(
                io.StringIO(csv_data),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=inventory_{date.today()}.csv"}
            )
        else:
            report = await ReportsService.get_inventory_report()
            return report
    except Exception as e:
        logger.error(f"Error generating inventory report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate inventory report"
        )

@reports_router.get("/financial", summary="Get financial summary report")
async def get_financial_report(
    start_date: date = Query(..., description="Start date for report"),
    end_date: date = Query(..., description="End date for report"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    try:
        report = await ReportsService.get_financial_report(start_date, end_date)
        return report
    except Exception as e:
        logger.error(f"Error generating financial report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate financial report"
        )

@reports_router.get("/customer-activity", summary="Get customer activity report")
async def get_customer_activity_report(
    start_date: date = Query(..., description="Start date for report"),
    end_date: date = Query(..., description="End date for report"),
    min_transactions: int = Query(1, ge=1, description="Minimum number of transactions"),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    try:
        report = await ReportsService.get_customer_activity_report(
            start_date, end_date, min_transactions
        )
        return report
    except Exception as e:
        logger.error(f"Error generating customer activity report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate customer activity report"
        )

@reports_router.get("/aged-loans", summary="Get aged loans report")
async def get_aged_loans_report(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    try:
        report = await ReportsService.get_aged_loans_report()
        return report
    except Exception as e:
        logger.error(f"Error generating aged loans report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate aged loans report"
        )