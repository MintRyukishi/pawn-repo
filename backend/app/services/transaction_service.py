# backend/app/services/transaction_service.py
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, date, timedelta
from app.models.transaction_model import Transaction, TransactionType, TransactionStatus, LoanStatus, PaymentMethod
from app.models.customer_model import Customer
from app.models.item_model import Item, ItemStatus
from app.schemas.transaction_schema import (
    PawnTransactionCreate, PaymentCreate, PaymentResultOut, PaymentAllocationOut,
    LoanStatusOut, LoanScenarioOut, StoreScenarioResponse, TransactionSearch
)
from beanie.operators import And
import logging
import secrets
import string

logger = logging.getLogger(__name__)

class TransactionService:
    
    @staticmethod
    def generate_receipt_number() -> str:
        """Generate unique receipt number"""
        timestamp = datetime.now().strftime("%Y%m%d")
        random_suffix = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        return f"PWN-{timestamp}-{random_suffix}"

    @staticmethod
    async def create_pawn_loan(pawn_data: PawnTransactionCreate, created_by: UUID) -> Transaction:
        """Create a new pawn loan transaction"""
        try:
            # Verify customer exists and can transact
            customer = await Customer.find_one(Customer.customer_id == pawn_data.customer_id)
            if not customer:
                raise ValueError("Customer not found")
            if not customer.can_transact:
                raise ValueError(f"Customer cannot transact - status: {customer.status}")
            
            # Verify item exists and is available
            item = await Item.find_one(Item.item_id == pawn_data.item_id)
            if not item:
                raise ValueError("Item not found")
            if item.status != ItemStatus.ACTIVE:
                raise ValueError(f"Item is not available for pawn - status: {item.status}")
            
            # Calculate dates
            pawn_date = date.today()
            due_date = pawn_date + timedelta(days=30)  # 1 month from today
            forfeit_date = due_date + timedelta(days=105)  # 3 months + 2 week grace
            
            # Create pawn transaction
            transaction = Transaction(
                transaction_type=TransactionType.PAWN,
                status=TransactionStatus.COMPLETED,
                total_amount=pawn_data.principal_amount,  # Principal amount goes to customer
                principal_amount=pawn_data.principal_amount,
                monthly_interest_fee=pawn_data.monthly_interest_fee,
                current_balance=pawn_data.principal_amount,  # Initial balance is principal
                payment_method=pawn_data.payment_method,
                customer_id=pawn_data.customer_id,
                item_id=pawn_data.item_id,
                loan_status=LoanStatus.ACTIVE,
                transaction_date=datetime.utcnow(),
                original_due_date=due_date,
                current_due_date=due_date,
                final_forfeit_date=forfeit_date,
                renewals_count=0,
                months_without_payment=0,
                receipt_number=TransactionService.generate_receipt_number(),
                notes=pawn_data.notes,
                created_by=created_by
            )
            
            await transaction.save()
            logger.info(f"Created pawn loan {transaction.transaction_id} for customer {customer.full_name}: ${pawn_data.principal_amount}")
            return transaction
            
        except Exception as e:
            logger.error(f"Error creating pawn loan: {str(e)}")
            raise

    @staticmethod
    async def process_payment(payment_data: PaymentCreate, processed_by: UUID) -> PaymentResultOut:
        """Process any type of payment with smart allocation"""
        try:
            # Get original loan
            loan = await Transaction.find_one(
                And(
                    Transaction.transaction_id == payment_data.loan_id,
                    Transaction.transaction_type == TransactionType.PAWN
                )
            )
            if not loan:
                raise ValueError("Loan not found")
            if not loan.is_loan_active:
                raise ValueError(f"Loan is not active - status: {loan.loan_status}")
            
            # Store original state
            original_balance = loan.current_balance or 0
            original_due_date = loan.current_due_date
            original_status = loan.loan_status
            
            # Validate payment is within allowed window
            if not loan.final_forfeit_date:
                raise ValueError("Loan has no forfeit date set")
            
            if payment_data.payment_date > loan.final_forfeit_date:
                raise ValueError(f"Payment date {payment_data.payment_date} is beyond grace period (ends: {loan.final_forfeit_date})")
            
            # Calculate payment allocation
            allocation = loan.process_payment_allocation(payment_data.payment_amount, payment_data.payment_date)
            
            # Determine transaction type based on allocation
            if allocation['payment_type'] == 'full_redemption':
                transaction_type = TransactionType.REDEMPTION
                new_loan_status = LoanStatus.REDEEMED
            elif allocation['principal_payment'] > 0:
                transaction_type = TransactionType.PARTIAL_PAYMENT
                new_loan_status = LoanStatus.ACTIVE
            else:
                transaction_type = TransactionType.RENEWAL
                new_loan_status = LoanStatus.ACTIVE
            
            # Create payment transaction
            payment_transaction = Transaction(
                transaction_type=transaction_type,
                status=TransactionStatus.COMPLETED,
                total_amount=payment_data.payment_amount,
                interest_amount=allocation['interest_payment'],
                principal_payment=allocation['principal_payment'],
                late_fee_amount=allocation['late_fee_payment'],
                payment_method=payment_data.payment_method,
                customer_id=loan.customer_id,
                item_id=loan.item_id,
                loan_id=loan.transaction_id,
                transaction_date=datetime.combine(payment_data.payment_date, datetime.now().time()),
                receipt_number=TransactionService.generate_receipt_number(),
                notes=payment_data.notes,
                created_by=processed_by
            )
            
            # Update the original loan
            loan.current_balance = allocation['new_balance']
            loan.current_due_date = allocation['new_due_date']
            loan.loan_status = new_loan_status
            loan.last_payment_date = payment_data.payment_date
            if allocation['months_extended'] > 0:
                loan.renewals_count += 1
            loan.months_without_payment = 0
            loan.updated_at = datetime.utcnow()
            
            # Update item status if redeemed
            if new_loan_status == LoanStatus.REDEEMED and loan.item_id:
                item = await Item.find_one(Item.item_id == loan.item_id)
                if item:
                    item.status = ItemStatus.REDEEMED
                    await item.save()
            
            # Save transactions
            await payment_transaction.save()
            await loan.save()
            
            # Create result
            payment_allocation_out = PaymentAllocationOut(**allocation)
            
            message = f"Payment processed successfully. "
            if allocation['payment_type'] == 'full_redemption':
                message += "Loan paid in full - item ready for pickup!"
            elif allocation['principal_payment'] > 0:
                message += f"Extended to {allocation['new_due_date'].strftime('%b %d, %Y')} with ${allocation['principal_payment']:.2f} applied to principal."
            else:
                message += f"Extended to {allocation['new_due_date'].strftime('%b %d, %Y')}."
            
            if allocation['overpayment'] > 0:
                message += f" Overpayment of ${allocation['overpayment']:.2f} noted."
            
            logger.info(f"Processed payment for loan {loan.transaction_id}: ${payment_data.payment_amount} ({allocation['payment_type']})")
            
            return PaymentResultOut(
                transaction=payment_transaction,
                payment_allocation=payment_allocation_out,
                original_balance=original_balance,
                original_due_date=original_due_date,
                loan_status_before=original_status.value,
                loan_status_after=new_loan_status.value,
                message=message
            )
            
        except Exception as e:
            logger.error(f"Error processing payment: {str(e)}")
            raise

    @staticmethod
    async def get_transaction_by_id(transaction_id: UUID) -> Optional[Transaction]:
        """Get transaction by ID"""
        return await Transaction.find_one(Transaction.transaction_id == transaction_id)

    @staticmethod
    async def mark_loan_forfeited(loan_id: UUID, processed_by: UUID) -> Transaction:
        """Mark a loan as forfeited"""
        try:
            # Get original loan
            loan = await Transaction.find_one(
                And(
                    Transaction.transaction_id == loan_id,
                    Transaction.transaction_type == TransactionType.PAWN
                )
            )
            if not loan:
                raise ValueError("Loan not found")
            
            # Check if eligible for forfeiture
            if not loan.check_forfeit_eligibility():
                raise ValueError(f"Loan not eligible for forfeiture until {loan.final_forfeit_date}")
            
            # Process forfeiture using the model method
            forfeit_transaction = await loan.mark_forfeited(processed_by)
            forfeit_transaction.receipt_number = TransactionService.generate_receipt_number()
            await forfeit_transaction.save()
            
            # Update item status to forfeited
            if loan.item_id:
                item = await Item.find_one(Item.item_id == loan.item_id)
                if item:
                    item.status = ItemStatus.FORFEITED
                    await item.save()
            
            logger.info(f"Marked loan {loan.transaction_id} as forfeited")
            return forfeit_transaction
            
        except Exception as e:
            logger.error(f"Error marking loan forfeited: {str(e)}")
            raise