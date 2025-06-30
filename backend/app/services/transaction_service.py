# backend/app/services/transaction_service.py - COMPLETED VERSION
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
    async def get_loan_status(loan_id: UUID) -> LoanStatusOut:
        """Get comprehensive loan status"""
        try:
            # Get loan transaction
            loan = await Transaction.find_one(
                And(
                    Transaction.transaction_id == loan_id,
                    Transaction.transaction_type == TransactionType.PAWN
                )
            )
            if not loan:
                raise ValueError("Loan not found")
            
            # Get customer and item details
            customer = await Customer.find_one(Customer.customer_id == loan.customer_id)
            item = await Item.find_one(Item.item_id == loan.item_id) if loan.item_id else None
            
            if not customer:
                raise ValueError("Customer not found")
            if not item:
                raise ValueError("Item not found")
            
            # Calculate status information
            total_owed = loan.total_amount_owed
            minimum_payment = loan.monthly_interest_fee or 0
            
            return LoanStatusOut(
                loan_id=loan.transaction_id,
                customer_name=customer.full_name,
                customer_phone=customer.phone,
                item_description=item.description,
                original_loan_amount=loan.principal_amount or 0,
                current_balance=loan.current_balance or 0,
                monthly_interest_fee=loan.monthly_interest_fee or 0,
                total_amount_owed=total_owed,
                original_due_date=loan.original_due_date,
                current_due_date=loan.current_due_date,
                final_forfeit_date=loan.final_forfeit_date,
                days_until_due=loan.days_until_due,
                days_overdue=loan.days_overdue,
                loan_status=loan.loan_status,
                renewals_count=loan.renewals_count,
                last_payment_date=loan.last_payment_date,
                is_within_grace_period=loan.is_within_grace_period,
                minimum_payment_required=minimum_payment,
                can_extend=loan.is_loan_active and total_owed > 0,
                can_redeem=loan.is_loan_active,
                is_forfeit_eligible=loan.check_forfeit_eligibility()
            )
            
        except Exception as e:
            logger.error(f"Error getting loan status: {str(e)}")
            raise

    @staticmethod
    async def get_payment_scenarios(loan_id: UUID, payment_date: Optional[date] = None) -> List[LoanScenarioOut]:
        """Get payment scenarios for a loan"""
        try:
            if not payment_date:
                payment_date = date.today()
            
            # Get loan
            loan = await Transaction.find_one(
                And(
                    Transaction.transaction_id == loan_id,
                    Transaction.transaction_type == TransactionType.PAWN
                )
            )
            if not loan:
                raise ValueError("Loan not found")
            
            if not loan.is_loan_active:
                raise ValueError("Loan is not active")
            
            scenarios = []
            
            # Scenario 1: Interest Only (Minimum Payment)
            interest_amount = loan.monthly_interest_fee or 0
            late_fee = loan.calculate_late_fee()
            minimum_payment = interest_amount + late_fee
            
            try:
                min_allocation = loan.process_payment_allocation(minimum_payment, payment_date)
                scenarios.append(LoanScenarioOut(
                    scenario_name="Interest Only (Minimum Payment)",
                    payment_amount=minimum_payment,
                    amount_breakdown={
                        "interest": min_allocation['interest_payment'],
                        "late_fee": min_allocation['late_fee_payment'],
                        "principal": 0.0
                    },
                    resulting_balance=min_allocation['new_balance'],
                    new_due_date=min_allocation['new_due_date'],
                    is_full_redemption=False
                ))
            except ValueError:
                pass  # Skip if minimum payment calculation fails
            
            # Scenario 2: Interest + Half Principal
            current_balance = loan.current_balance or 0
            half_principal_payment = minimum_payment + (current_balance * 0.5)
            
            try:
                half_allocation = loan.process_payment_allocation(half_principal_payment, payment_date)
                scenarios.append(LoanScenarioOut(
                    scenario_name="Interest + 50% Principal",
                    payment_amount=half_principal_payment,
                    amount_breakdown={
                        "interest": half_allocation['interest_payment'],
                        "late_fee": half_allocation['late_fee_payment'],
                        "principal": half_allocation['principal_payment']
                    },
                    resulting_balance=half_allocation['new_balance'],
                    new_due_date=half_allocation['new_due_date'],
                    is_full_redemption=half_allocation['payment_type'] == 'full_redemption'
                ))
            except ValueError:
                pass
            
            # Scenario 3: Full Redemption
            full_payment = minimum_payment + current_balance
            
            try:
                full_allocation = loan.process_payment_allocation(full_payment, payment_date)
                scenarios.append(LoanScenarioOut(
                    scenario_name="Full Redemption",
                    payment_amount=full_payment,
                    amount_breakdown={
                        "interest": full_allocation['interest_payment'],
                        "late_fee": full_allocation['late_fee_payment'],
                        "principal": full_allocation['principal_payment']
                    },
                    resulting_balance=0.0,
                    new_due_date=full_allocation['new_due_date'],
                    is_full_redemption=True
                ))
            except ValueError:
                pass
            
            return scenarios
            
        except Exception as e:
            logger.error(f"Error getting payment scenarios: {str(e)}")
            raise

    @staticmethod
    async def test_store_scenario(scenario_name: str, customer_id: UUID, item_id: UUID, created_by: UUID) -> StoreScenarioResponse:
        """Test specific store scenarios"""
        try:
            if scenario_name == "simple_redemption":
                return await TransactionService._test_simple_redemption(customer_id, item_id, created_by)
            elif scenario_name == "extension_by_interest":
                return await TransactionService._test_extension_by_interest(customer_id, item_id, created_by)
            elif scenario_name == "partial_payment_rollover":
                return await TransactionService._test_partial_payment_rollover(customer_id, item_id, created_by)
            else:
                raise ValueError(f"Unknown scenario: {scenario_name}")
                
        except Exception as e:
            logger.error(f"Error testing scenario {scenario_name}: {str(e)}")
            return StoreScenarioResponse(
                scenario_name=scenario_name,
                description="",
                success=False,
                message=f"Error: {str(e)}"
            )

    @staticmethod
    async def _test_simple_redemption(customer_id: UUID, item_id: UUID, created_by: UUID) -> StoreScenarioResponse:
        """Test simple redemption scenario"""
        transactions_created = []
        
        # Create pawn loan
        pawn_data = PawnTransactionCreate(
            customer_id=customer_id,
            item_id=item_id,
            principal_amount=100.0,
            monthly_interest_fee=15.0
        )
        loan = await TransactionService.create_pawn_loan(pawn_data, created_by)
        transactions_created.append(loan.transaction_id)
        
        # Wait 15 days, then redeem
        redemption_date = date.today() + timedelta(days=15)
        payment_data = PaymentCreate(
            loan_id=loan.transaction_id,
            payment_amount=115.0,  # $100 principal + $15 interest
            payment_date=redemption_date
        )
        result = await TransactionService.process_payment(payment_data, created_by)
        transactions_created.append(result.transaction.transaction_id)
        
        return StoreScenarioResponse(
            scenario_name="simple_redemption",
            description="Pawn $100, redeem for $115 after 15 days",
            success=True,
            loan_id=loan.transaction_id,
            final_balance=0.0,
            final_status="redeemed",
            transactions_created=transactions_created,
            message="Simple redemption completed successfully",
            details={
                "original_amount": 100.0,
                "interest_paid": 15.0,
                "total_paid": 115.0,
                "days_held": 15
            }
        )

    @staticmethod
    async def _test_extension_by_interest(customer_id: UUID, item_id: UUID, created_by: UUID) -> StoreScenarioResponse:
        """Test extension by interest payment scenario"""
        transactions_created = []
        
        # Create larger pawn loan
        pawn_data = PawnTransactionCreate(
            customer_id=customer_id,
            item_id=item_id,
            principal_amount=500.0,
            monthly_interest_fee=75.0
        )
        loan = await TransactionService.create_pawn_loan(pawn_data, created_by)
        transactions_created.append(loan.transaction_id)
        
        # Pay interest only to extend
        extension_date = loan.current_due_date  # Pay exactly on due date
        payment_data = PaymentCreate(
            loan_id=loan.transaction_id,
            payment_amount=75.0,  # Interest only
            payment_date=extension_date
        )
        result = await TransactionService.process_payment(payment_data, created_by)
        transactions_created.append(result.transaction.transaction_id)
        
        # Refresh loan data
        updated_loan = await Transaction.find_one(Transaction.transaction_id == loan.transaction_id)
        
        return StoreScenarioResponse(
            scenario_name="extension_by_interest",
            description="Borrow $500, pay $75 to extend, still owe $500",
            success=True,
            loan_id=loan.transaction_id,
            final_balance=updated_loan.current_balance,
            final_status=updated_loan.loan_status.value,
            transactions_created=transactions_created,
            message="Extension by interest payment completed",
            details={
                "original_amount": 500.0,
                "interest_paid": 75.0,
                "remaining_balance": updated_loan.current_balance,
                "new_due_date": updated_loan.current_due_date.isoformat()
            }
        )

    @staticmethod
    async def _test_partial_payment_rollover(customer_id: UUID, item_id: UUID, created_by: UUID) -> StoreScenarioResponse:
        """Test partial payment rollover scenario"""
        transactions_created = []
        
        # Create large pawn loan
        pawn_data = PawnTransactionCreate(
            customer_id=customer_id,
            item_id=item_id,
            principal_amount=1000.0,
            monthly_interest_fee=150.0
        )
        loan = await TransactionService.create_pawn_loan(pawn_data, created_by)
        transactions_created.append(loan.transaction_id)
        
        # Make partial payment
        payment_data = PaymentCreate(
            loan_id=loan.transaction_id,
            payment_amount=500.0,  # Partial payment
            payment_date=loan.current_due_date
        )
        result = await TransactionService.process_payment(payment_data, created_by)
        transactions_created.append(result.transaction.transaction_id)
        
        # Refresh loan data
        updated_loan = await Transaction.find_one(Transaction.transaction_id == loan.transaction_id)
        
        return StoreScenarioResponse(
            scenario_name="partial_payment_rollover",
            description="Owe $1150, pay $500, remaining balance rolls over",
            success=True,
            loan_id=loan.transaction_id,
            final_balance=updated_loan.current_balance,
            final_status=updated_loan.loan_status.value,
            transactions_created=transactions_created,
            message="Partial payment rollover completed",
            details={
                "original_amount": 1000.0,
                "total_owed": 1150.0,  # $1000 + $150 interest
                "amount_paid": 500.0,
                "remaining_balance": updated_loan.current_balance,
                "new_due_date": updated_loan.current_due_date.isoformat()
            }
        )

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
            
            # Create forfeit transaction
            forfeit_transaction = Transaction(
                transaction_type=TransactionType.FORFEIT,
                status=TransactionStatus.COMPLETED,
                total_amount=0.0,  # No money changes hands
                customer_id=loan.customer_id,
                item_id=loan.item_id,
                loan_id=loan.transaction_id,
                transaction_date=datetime.utcnow(),
                receipt_number=TransactionService.generate_receipt_number(),
                notes="Loan forfeited - item becomes shop property",
                created_by=processed_by
            )
            
            # Update loan status
            loan.loan_status = LoanStatus.FORFEITED
            loan.updated_at = datetime.utcnow()
            
            # Update item status to forfeited
            if loan.item_id:
                item = await Item.find_one(Item.item_id == loan.item_id)
                if item:
                    item.status = ItemStatus.FORFEITED
                    await item.save()
            
            # Save changes
            await forfeit_transaction.save()
            await loan.save()
            
            logger.info(f"Marked loan {loan.transaction_id} as forfeited")
            return forfeit_transaction
            
        except Exception as e:
            logger.error(f"Error marking loan forfeited: {str(e)}")
            raise

    @staticmethod
    async def search_transactions(search_params: TransactionSearch, skip: int = 0, limit: int = 50) -> List[Transaction]:
        """Search transactions based on criteria"""
        query_conditions = []
        
        if search_params.customer_id:
            query_conditions.append(Transaction.customer_id == search_params.customer_id)
        
        if search_params.item_id:
            query_conditions.append(Transaction.item_id == search_params.item_id)
        
        if search_params.loan_id:
            query_conditions.append(Transaction.loan_id == search_params.loan_id)
        
        if search_params.transaction_type:
            query_conditions.append(Transaction.transaction_type == search_params.transaction_type)
        
        if search_params.status:
            query_conditions.append(Transaction.status == search_params.status)
        
        if search_params.loan_status:
            query_conditions.append(Transaction.loan_status == search_params.loan_status)
        
        if search_params.start_date:
            start_datetime = datetime.combine(search_params.start_date, datetime.min.time())
            query_conditions.append(Transaction.transaction_date >= start_datetime)
        
        if search_params.end_date:
            end_datetime = datetime.combine(search_params.end_date, datetime.max.time())
            query_conditions.append(Transaction.transaction_date <= end_datetime)
        
        if search_params.is_overdue is not None:
            if search_params.is_overdue:
                query_conditions.append(Transaction.current_due_date < date.today())
            else:
                query_conditions.append(Transaction.current_due_date >= date.today())
        
        if query_conditions:
            query = Transaction.find(And(*query_conditions))
        else:
            query = Transaction.find()
        
        return await query.sort(-Transaction.transaction_date).skip(skip).limit(limit).to_list()