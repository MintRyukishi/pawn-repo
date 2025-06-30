# backend/app/models/transaction_model.py
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from uuid import UUID, uuid4
from beanie import Document
from pydantic import Field, computed_field
from enum import Enum

class TransactionType(str, Enum):
    PAWN = "pawn"                    # Customer pawns an item
    RENEWAL = "renewal"              # Monthly renewal payment (interest only)
    PARTIAL_PAYMENT = "partial_payment"  # Partial payment toward principal + interest
    REDEMPTION = "redemption"        # Customer pays full amount to get item back
    FORFEIT = "forfeit"             # Item becomes shop property
    SALE = "sale"                   # Shop sells forfeited item
    LATE_FEE = "late_fee"           # Late payment fee

class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentMethod(str, Enum):
    CASH = "cash"                    # Only payment method for now

class LoanStatus(str, Enum):
    ACTIVE = "active"               # Loan is current
    OVERDUE = "overdue"            # Past due date but within grace period
    DEFAULT = "default"            # Beyond grace period - ready for forfeit
    REDEEMED = "redeemed"          # Principal paid back, item returned
    FORFEITED = "forfeited"        # Item became shop property

class Transaction(Document):
    transaction_id: UUID = Field(default_factory=uuid4)
    
    # Transaction details
    transaction_type: TransactionType
    status: TransactionStatus = Field(default=TransactionStatus.PENDING)
    
    # Financial amounts
    total_amount: float = Field(..., ge=0, description="Total transaction amount")
    principal_amount: Optional[float] = Field(None, ge=0, description="Principal loan amount (for pawn transactions)")
    interest_amount: Optional[float] = Field(None, ge=0, description="Interest/renewal fee amount")
    late_fee_amount: Optional[float] = Field(None, ge=0, description="Late fee amount")
    principal_payment: Optional[float] = Field(None, ge=0, description="Amount applied to principal")
    
    # Payment details
    payment_method: PaymentMethod = Field(default=PaymentMethod.CASH)
    
    # References
    customer_id: UUID = Field(..., description="Customer involved in transaction")
    item_id: Optional[UUID] = Field(None, description="Item involved (if applicable)")
    loan_id: Optional[UUID] = Field(None, description="Original loan transaction for renewals/payments")
    
    # Loan-specific fields (for PAWN transactions)
    loan_status: Optional[LoanStatus] = Field(None, description="Current loan status")
    monthly_interest_fee: Optional[float] = Field(None, ge=0, description="Monthly interest fee for this loan")
    current_balance: Optional[float] = Field(None, ge=0, description="Current amount owed (principal + accumulated interest)")
    
    # Important dates
    transaction_date: datetime = Field(default_factory=datetime.utcnow)
    original_due_date: Optional[date] = Field(None, description="Original payment due date (1 month from pawn)")
    current_due_date: Optional[date] = Field(None, description="Current due date (updated with renewals)")
    final_forfeit_date: Optional[date] = Field(None, description="Date item will be forfeited (3 months + 2 week grace)")
    
    # Renewal tracking
    renewals_count: int = Field(default=0, description="Number of times this loan has been renewed")
    last_payment_date: Optional[date] = Field(None, description="Date of last payment")
    months_without_payment: int = Field(default=0, description="Consecutive months without payment")
    
    # Receipt and audit
    receipt_number: Optional[str] = Field(None, description="Receipt number for customer")
    notes: Optional[str] = Field(None, max_length=1000, description="Transaction notes")
    created_by: UUID = Field(..., description="Staff member who processed transaction")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Transaction {self.transaction_type.value} - ${self.total_amount}>"

    def __str__(self) -> str:
        return f"{self.transaction_type.value.title()} - ${self.total_amount}"

    @computed_field
    @property
    def is_loan_active(self) -> bool:
        """Check if this is an active loan"""
        return self.transaction_type == TransactionType.PAWN and self.loan_status == LoanStatus.ACTIVE

    @computed_field
    @property
    def days_until_due(self) -> Optional[int]:
        """Days until current due date"""
        if not self.current_due_date:
            return None
        return (self.current_due_date - date.today()).days

    @computed_field
    @property
    def is_overdue(self) -> bool:
        """Check if loan is overdue"""
        if not self.current_due_date:
            return False
        return date.today() > self.current_due_date

    @computed_field
    @property
    def days_overdue(self) -> int:
        """Days past due date"""
        if not self.is_overdue:
            return 0
        return (date.today() - self.current_due_date).days

    @computed_field
    @property
    def is_within_grace_period(self) -> bool:
        """Check if within 1-week grace period after due date"""
        if not self.is_overdue:
            return True
        return self.days_overdue <= 7

    @computed_field
    @property
    def total_amount_owed(self) -> float:
        """Calculate total amount currently owed"""
        if not self.is_loan_active:
            return 0.0
        
        # Start with current balance (principal + any accumulated interest)
        base_amount = self.current_balance or (self.principal_amount or 0)
        
        # Add current month's interest if due
        if self.current_due_date and date.today() >= self.current_due_date:
            base_amount += (self.monthly_interest_fee or 0)
        
        return base_amount

    def calculate_amount_owed_at_date(self, target_date: date) -> float:
        """Calculate amount owed at a specific date"""
        if not self.is_loan_active or not self.current_due_date or not self.monthly_interest_fee:
            return self.current_balance or 0
        
        base_amount = self.current_balance or 0
        
        # If target date is past current due date, add interest
        if target_date >= self.current_due_date:
            base_amount += self.monthly_interest_fee
        
        return base_amount

    def calculate_late_fee(self) -> float:
        """Calculate late fee based on days overdue"""
        if not self.is_overdue or self.is_within_grace_period:
            return 0.0
        
        # Beyond 1 week = $10 late fee (configurable)
        return 10.0

    def calculate_next_due_date_from_original(self, months_to_add: int) -> date:
        """Calculate next due date from original due date (store policy)"""
        if not self.original_due_date:
            return date.today() + timedelta(days=30 * months_to_add)
        
        next_date = self.original_due_date
        for _ in range(months_to_add):
            try:
                if next_date.month == 12:
                    next_date = next_date.replace(year=next_date.year + 1, month=1)
                else:
                    next_date = next_date.replace(month=next_date.month + 1)
            except ValueError:
                # Handle month-end edge cases
                import calendar
                next_month = 1 if next_date.month == 12 else next_date.month + 1
                next_year = next_date.year + 1 if next_date.month == 12 else next_date.year
                last_day = calendar.monthrange(next_year, next_month)[1]
                next_date = next_date.replace(
                    year=next_year,
                    month=next_month,
                    day=min(next_date.day, last_day)
                )
        return next_date

    def calculate_forfeit_date(self) -> date:
        """Calculate forfeiture date (3 months + 2 week grace period)"""
        if not self.original_due_date:
            return date.today() + timedelta(days=105)  # ~3.5 months
        
        # 3 months from original due date + 2 weeks grace
        three_months_later = self.calculate_next_due_date_from_original(3)
        return three_months_later + timedelta(days=14)

    def process_payment_allocation(self, payment_amount: float, payment_date: date) -> Dict[str, Any]:
        """
        Process payment allocation based on store scenarios
        """
        if not self.monthly_interest_fee or not self.current_balance:
            raise ValueError("Invalid loan state for payment processing")
        
        current_interest_due = self.monthly_interest_fee
        current_total_owed = self.calculate_amount_owed_at_date(payment_date)
        
        # Minimum payment is interest amount
        if payment_amount < current_interest_due:
            raise ValueError(f"Minimum payment is ${current_interest_due:.2f} (interest amount). Paid: ${payment_amount:.2f}")
        
        allocation = {
            'payment_amount': payment_amount,
            'interest_payment': 0.0,
            'principal_payment': 0.0,
            'late_fee_payment': 0.0,
            'overpayment': 0.0,
            'payment_type': '',
            'new_balance': self.current_balance,
            'months_extended': 0,
            'new_due_date': self.current_due_date
        }
        
        remaining_payment = payment_amount
        
        # 1. Pay late fee first (if applicable)
        late_fee = self.calculate_late_fee()
        if late_fee > 0:
            fee_payment = min(remaining_payment, late_fee)
            allocation['late_fee_payment'] = fee_payment
            remaining_payment -= fee_payment
        
        # 2. Pay interest (minimum requirement)
        if remaining_payment >= current_interest_due:
            allocation['interest_payment'] = current_interest_due
            remaining_payment -= current_interest_due
            allocation['months_extended'] = 1
            
            # 3. Apply any remaining to principal
            if remaining_payment > 0:
                if remaining_payment >= self.current_balance:
                    # Full redemption
                    allocation['principal_payment'] = self.current_balance
                    allocation['new_balance'] = 0.0
                    allocation['payment_type'] = 'full_redemption'
                    allocation['overpayment'] = remaining_payment - self.current_balance
                else:
                    # Partial principal payment
                    allocation['principal_payment'] = remaining_payment
                    allocation['new_balance'] = self.current_balance - remaining_payment
                    allocation['payment_type'] = 'renewal_with_principal'
            else:
                allocation['payment_type'] = 'interest_only_renewal'
        
        # Calculate new due date (always from original due date per store policy)
        if allocation['months_extended'] > 0:
            # Find current month number from original due date
            months_since_original = 1
            if self.current_due_date and self.original_due_date:
                months_since_original = ((self.current_due_date.year - self.original_due_date.year) * 12 + 
                                       (self.current_due_date.month - self.original_due_date.month)) + 1
            
            new_month_number = months_since_original + allocation['months_extended']
            allocation['new_due_date'] = self.calculate_next_due_date_from_original(new_month_number)
        
        return allocation

    class Settings:
        name = "transactions"
        indexes = [
            [("customer_id", 1), ("transaction_date", -1)],
            [("item_id", 1), ("transaction_type", 1)],
            [("loan_id", 1), ("transaction_type", 1)],
            [("transaction_type", 1), ("status", 1), ("transaction_date", -1)],
            [("loan_status", 1), ("current_due_date", 1)],
            [("current_due_date", 1)],
            [("final_forfeit_date", 1)],
            [("receipt_number", 1)]
        ]