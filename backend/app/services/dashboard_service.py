# backend/app/services/dashboard_service.py - FIXED VERSION
from typing import Dict, List, Any
from datetime import datetime, date, timedelta
from app.models.customer_model import Customer, CustomerStatus
from app.models.item_model import Item, ItemStatus
from app.models.transaction_model import Transaction, TransactionType, TransactionStatus, LoanStatus
from beanie.operators import And
import logging

logger = logging.getLogger(__name__)

class DashboardService:
    @staticmethod
    async def get_overview() -> Dict[str, Any]:
        """Get high-level dashboard overview"""
        try:
            # Get basic counts
            total_customers = await Customer.find().count()
            active_customers = await Customer.find(Customer.status == CustomerStatus.ACTIVE).count()
            total_items = await Item.find().count()
            active_loans = await Item.find(Item.status == ItemStatus.ACTIVE).count()
            
            # Get today's transactions
            today = date.today()
            start_of_day = datetime.combine(today, datetime.min.time())
            end_of_day = datetime.combine(today, datetime.max.time())
            
            today_transactions = await Transaction.find(
                And(
                    Transaction.transaction_date >= start_of_day,
                    Transaction.transaction_date <= end_of_day,
                    Transaction.status == TransactionStatus.COMPLETED
                )
            ).to_list()
            
            # Calculate today's metrics
            today_revenue = sum(
                t.total_amount for t in today_transactions 
                if t.transaction_type in [TransactionType.RENEWAL, TransactionType.REDEMPTION, TransactionType.PARTIAL_PAYMENT]
            )
            today_loans = sum(
                t.principal_amount or 0 for t in today_transactions 
                if t.transaction_type == TransactionType.PAWN
            )
            
            return {
                "customers": {
                    "total": total_customers,
                    "active": active_customers,
                    "inactive": total_customers - active_customers
                },
                "items": {
                    "total": total_items,
                    "active_loans": active_loans,
                    "available": total_items - active_loans
                },
                "today": {
                    "transactions": len(today_transactions),
                    "revenue": today_revenue,
                    "loans_issued": today_loans
                }
            }
        except Exception as e:
            logger.error(f"Error getting dashboard overview: {str(e)}")
            raise

    @staticmethod
    async def get_statistics(days: int) -> Dict[str, Any]:
        """Get statistics for the specified number of days"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            transactions = await Transaction.find(
                And(
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                    Transaction.status == TransactionStatus.COMPLETED
                )
            ).to_list()
            
            # Group by transaction type
            pawn_transactions = [t for t in transactions if t.transaction_type == TransactionType.PAWN]
            payment_transactions = [t for t in transactions if t.transaction_type in [
                TransactionType.RENEWAL, TransactionType.PARTIAL_PAYMENT
            ]]
            redemption_transactions = [t for t in transactions if t.transaction_type == TransactionType.REDEMPTION]
            
            # Calculate totals
            total_revenue = sum(
                t.total_amount for t in transactions 
                if t.transaction_type != TransactionType.PAWN
            )
            total_loans_issued = sum(t.principal_amount or 0 for t in pawn_transactions)
            
            return {
                "period_days": days,
                "total_transactions": len(transactions),
                "total_revenue": total_revenue,
                "total_loans_issued": total_loans_issued,
                "pawn_stats": {
                    "count": len(pawn_transactions),
                    "total_amount": total_loans_issued,
                    "average_loan": total_loans_issued / len(pawn_transactions) if pawn_transactions else 0
                },
                "payment_stats": {
                    "count": len(payment_transactions),
                    "total_amount": sum(t.total_amount for t in payment_transactions)
                },
                "redemption_stats": {
                    "count": len(redemption_transactions),
                    "total_amount": sum(t.total_amount for t in redemption_transactions)
                }
            }
        except Exception as e:
            logger.error(f"Error getting dashboard statistics: {str(e)}")
            raise

    @staticmethod
    async def get_recent_transactions(limit: int) -> List[Dict[str, Any]]:
        """Get recent transactions"""
        try:
            transactions = await Transaction.find(
                Transaction.status == TransactionStatus.COMPLETED
            ).sort(-Transaction.transaction_date).limit(limit).to_list()
            
            result = []
            for transaction in transactions:
                # Get customer and item details
                customer = await Customer.find_one(Customer.customer_id == transaction.customer_id)
                item = None
                if transaction.item_id:
                    item = await Item.find_one(Item.item_id == transaction.item_id)
                
                result.append({
                    "transaction_id": transaction.transaction_id,
                    "type": transaction.transaction_type.value,
                    "amount": transaction.total_amount,
                    "customer_name": f"{customer.first_name} {customer.last_name}" if customer else "Unknown",
                    "item_name": item.description if item else None,
                    "date": transaction.transaction_date,
                    "receipt_number": transaction.receipt_number
                })
            
            return result
        except Exception as e:
            logger.error(f"Error getting recent transactions: {str(e)}")
            raise

    @staticmethod
    async def get_due_items(days_ahead: int) -> List[Dict[str, Any]]:
        """Get items with payments due in the next N days"""
        try:
            end_date = date.today() + timedelta(days=days_ahead)
            
            # Find active pawn loans with due dates in the specified range
            transactions = await Transaction.find(
                And(
                    Transaction.transaction_type == TransactionType.PAWN,
                    Transaction.loan_status == LoanStatus.ACTIVE,
                    Transaction.current_due_date <= end_date,
                    Transaction.current_due_date >= date.today()
                )
            ).to_list()
            
            result = []
            for transaction in transactions:
                customer = await Customer.find_one(Customer.customer_id == transaction.customer_id)
                item = await Item.find_one(Item.item_id == transaction.item_id) if transaction.item_id else None
                
                if customer and item and item.status == ItemStatus.ACTIVE:
                    result.append({
                        "transaction_id": transaction.transaction_id,
                        "customer_name": f"{customer.first_name} {customer.last_name}",
                        "customer_phone": customer.phone,
                        "item_name": item.description,
                        "loan_amount": transaction.principal_amount or 0,
                        "current_balance": transaction.current_balance or 0,
                        "monthly_interest": transaction.monthly_interest_fee or 0,
                        "due_date": transaction.current_due_date,
                        "days_until_due": (transaction.current_due_date - date.today()).days if transaction.current_due_date else None
                    })
            
            # Sort by due date
            result.sort(key=lambda x: x["due_date"] if x["due_date"] else date.max)
            return result
        except Exception as e:
            logger.error(f"Error getting due items: {str(e)}")
            raise

    @staticmethod
    async def get_overdue_items() -> List[Dict[str, Any]]:
        """Get overdue items"""
        try:
            today = date.today()
            
            # Find active loans that are overdue
            transactions = await Transaction.find(
                And(
                    Transaction.transaction_type == TransactionType.PAWN,
                    Transaction.loan_status == LoanStatus.ACTIVE,
                    Transaction.current_due_date < today
                )
            ).to_list()
            
            result = []
            for transaction in transactions:
                customer = await Customer.find_one(Customer.customer_id == transaction.customer_id)
                item = await Item.find_one(Item.item_id == transaction.item_id) if transaction.item_id else None
                
                if customer and item and item.status == ItemStatus.ACTIVE:
                    days_overdue = (today - transaction.current_due_date).days if transaction.current_due_date else 0
                    
                    result.append({
                        "transaction_id": transaction.transaction_id,
                        "customer_name": f"{customer.first_name} {customer.last_name}",
                        "customer_phone": customer.phone,
                        "item_name": item.description,
                        "loan_amount": transaction.principal_amount or 0,
                        "current_balance": transaction.current_balance or 0,
                        "monthly_interest": transaction.monthly_interest_fee or 0,
                        "due_date": transaction.current_due_date,
                        "days_overdue": days_overdue,
                        "final_forfeit_date": transaction.final_forfeit_date,
                        "is_forfeit_eligible": transaction.check_forfeit_eligibility() if hasattr(transaction, 'check_forfeit_eligibility') else False
                    })
            
            # Sort by days overdue (most overdue first)
            result.sort(key=lambda x: x["days_overdue"], reverse=True)
            return result
        except Exception as e:
            logger.error(f"Error getting overdue items: {str(e)}")
            raise

    @staticmethod
    async def get_performance_metrics(start_date: date, end_date: date) -> Dict[str, Any]:
        """Get performance metrics for a date range"""
        try:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            transactions = await Transaction.find(
                And(
                    Transaction.transaction_date >= start_datetime,
                    Transaction.transaction_date <= end_datetime,
                    Transaction.status == TransactionStatus.COMPLETED
                )
            ).to_list()
            
            # Calculate metrics
            pawn_transactions = [t for t in transactions if t.transaction_type == TransactionType.PAWN]
            redemption_transactions = [t for t in transactions if t.transaction_type == TransactionType.REDEMPTION]
            payment_transactions = [t for t in transactions if t.transaction_type in [
                TransactionType.RENEWAL, TransactionType.PARTIAL_PAYMENT
            ]]
            
            total_revenue = sum(
                t.total_amount for t in transactions 
                if t.transaction_type != TransactionType.PAWN
            )
            total_loans = sum(t.principal_amount or 0 for t in pawn_transactions)
            
            pawn_count = len(pawn_transactions)
            redemption_count = len(redemption_transactions)
            
            # Calculate redemption rate
            redemption_rate = (redemption_count / pawn_count * 100) if pawn_count > 0 else 0
            
            # Calculate daily averages
            days_in_period = (end_date - start_date).days + 1
            avg_daily_revenue = total_revenue / days_in_period if days_in_period > 0 else 0
            avg_daily_loans = total_loans / days_in_period if days_in_period > 0 else 0
            
            # Calculate interest collected
            total_interest = sum(
                t.interest_amount or 0 for t in transactions 
                if t.transaction_type in [TransactionType.RENEWAL, TransactionType.REDEMPTION, TransactionType.PARTIAL_PAYMENT]
            )
            
            return {
                "period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "days": days_in_period
                },
                "totals": {
                    "revenue": total_revenue,
                    "loans_issued": total_loans,
                    "interest_collected": total_interest,
                    "transaction_count": len(transactions)
                },
                "averages": {
                    "daily_revenue": avg_daily_revenue,
                    "daily_loans": avg_daily_loans,
                    "transaction_amount": total_revenue / len(transactions) if transactions else 0
                },
                "rates": {
                    "redemption_rate": redemption_rate,
                    "interest_to_principal_ratio": (total_interest / total_loans * 100) if total_loans > 0 else 0
                },
                "breakdown": {
                    "pawn_transactions": pawn_count,
                    "payment_transactions": len(payment_transactions),
                    "redemption_transactions": redemption_count,
                    "forfeit_transactions": len([t for t in transactions if t.transaction_type == TransactionType.FORFEIT])
                }
            }
        except Exception as e:
            logger.error(f"Error getting performance metrics: {str(e)}")
            raise

    @staticmethod
    async def get_loan_portfolio_summary() -> Dict[str, Any]:
        """Get summary of current loan portfolio"""
        try:
            # Get all active loans
            active_loans = await Transaction.find(
                And(
                    Transaction.transaction_type == TransactionType.PAWN,
                    Transaction.loan_status == LoanStatus.ACTIVE
                )
            ).to_list()
            
            if not active_loans:
                return {
                    "total_loans": 0,
                    "total_principal_outstanding": 0,
                    "total_current_balance": 0,
                    "average_loan_amount": 0,
                    "loans_by_age": {"current": 0, "overdue": 0, "at_risk": 0},
                    "estimated_monthly_interest": 0
                }
            
            total_principal = sum(loan.principal_amount or 0 for loan in active_loans)
            total_balance = sum(loan.current_balance or 0 for loan in active_loans)
            total_monthly_interest = sum(loan.monthly_interest_fee or 0 for loan in active_loans)
            
            # Categorize loans by status
            current_loans = 0
            overdue_loans = 0
            at_risk_loans = 0
            
            for loan in active_loans:
                if loan.current_due_date:
                    days_until_due = (loan.current_due_date - date.today()).days
                    if days_until_due >= 0:
                        current_loans += 1
                    elif loan.is_within_grace_period:
                        overdue_loans += 1
                    else:
                        at_risk_loans += 1
                else:
                    current_loans += 1
            
            return {
                "total_loans": len(active_loans),
                "total_principal_outstanding": total_principal,
                "total_current_balance": total_balance,
                "average_loan_amount": total_principal / len(active_loans),
                "loans_by_age": {
                    "current": current_loans,
                    "overdue": overdue_loans,
                    "at_risk": at_risk_loans
                },
                "estimated_monthly_interest": total_monthly_interest
            }
        except Exception as e:
            logger.error(f"Error getting loan portfolio summary: {str(e)}")
            raise