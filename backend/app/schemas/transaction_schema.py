# backend/app/schemas/transaction_schema.py - FIXED FOR COPY-PASTE
from uuid import UUID
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.transaction_model import TransactionType, TransactionStatus, PaymentMethod, LoanStatus

class TransactionBase(BaseModel):
    transaction_type: TransactionType
    total_amount: float = Field(..., ge=0, description="Total transaction amount")
    payment_method: PaymentMethod = Field(default=PaymentMethod.CASH)
    notes: Optional[str] = Field(None, max_length=1000)

class PawnTransactionCreate(TransactionBase):
    """Create a new pawn loan"""
    transaction_type: TransactionType = Field(default=TransactionType.PAWN)
    customer_id: UUID
    item_id: UUID
    principal_amount: float = Field(..., gt=0, description="Loan principal amount")
    monthly_interest_fee: float = Field(..., gt=0, description="Monthly interest fee")

class PaymentCreate(BaseModel):
    """Process any type of payment (renewal, partial, redemption)"""
    loan_id: UUID = Field(..., description="Original pawn transaction ID")
    payment_amount: float = Field(..., gt=0, description="Amount being paid")
    payment_date: date = Field(..., description="Date when payment was made")
    payment_method: PaymentMethod = Field(default=PaymentMethod.CASH)
    notes: Optional[str] = Field(None, max_length=1000)

class TransactionUpdate(BaseModel):
    status: Optional[TransactionStatus] = None
    payment_method: Optional[PaymentMethod] = None
    notes: Optional[str] = Field(None, max_length=1000)

class PaymentAllocationOut(BaseModel):
    """Details of how a payment is allocated"""
    payment_amount: float = Field(..., description="Total amount paid")
    interest_payment: float = Field(..., description="Amount applied to interest")
    principal_payment: float = Field(..., description="Amount applied to principal")
    late_fee_payment: float = Field(..., description="Amount applied to late fees")
    overpayment: float = Field(..., description="Amount paid beyond what was owed")
    payment_type: str = Field(..., description="Type of payment processed")
    new_balance: float = Field(..., description="Remaining balance after payment")
    months_extended: int = Field(..., description="Number of months loan was extended")
    new_due_date: date = Field(..., description="New due date after payment")

class LoanScenarioOut(BaseModel):
    """Payment scenario option for a loan"""
    scenario_name: str = Field(..., description="Description of this payment option")
    payment_amount: float = Field(..., description="Amount to pay for this scenario")
    amount_breakdown: Dict[str, float] = Field(..., description="How payment would be allocated")
    resulting_balance: float = Field(..., description="Balance after this payment")
    new_due_date: date = Field(..., description="Due date after this payment")
    is_full_redemption: bool = Field(..., description="Whether this pays off the loan completely")

class TransactionOut(TransactionBase):
    transaction_id: UUID
    status: TransactionStatus
    
    # Financial details
    principal_amount: Optional[float]
    interest_amount: Optional[float]
    late_fee_amount: Optional[float]
    principal_payment: Optional[float]
    
    # References
    customer_id: UUID
    item_id: Optional[UUID]
    loan_id: Optional[UUID]
    
    # Loan details (for pawn transactions)
    loan_status: Optional[LoanStatus]
    monthly_interest_fee: Optional[float]
    current_balance: Optional[float]
    
    # Dates
    transaction_date: datetime
    original_due_date: Optional[date]
    current_due_date: Optional[date]
    final_forfeit_date: Optional[date]
    
    # Tracking
    renewals_count: int
    last_payment_date: Optional[date]
    months_without_payment: int
    
    # Computed fields
    is_loan_active: bool
    days_until_due: Optional[int]
    is_overdue: bool
    days_overdue: int
    is_within_grace_period: bool
    total_amount_owed: float
    
    # Receipt and audit
    receipt_number: Optional[str]
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PaymentResultOut(BaseModel):
    """Result of processing a payment"""
    transaction: TransactionOut
    payment_allocation: PaymentAllocationOut
    original_balance: float
    original_due_date: date
    loan_status_before: str
    loan_status_after: str
    message: str

class LoanStatusOut(BaseModel):
    """Current status of a loan"""
    loan_id: UUID
    customer_name: str
    customer_phone: str
    item_description: str
    
    # Financial status
    original_loan_amount: float
    current_balance: float
    monthly_interest_fee: float
    total_amount_owed: float
    
    # Date status
    original_due_date: date
    current_due_date: date
    final_forfeit_date: date
    days_until_due: Optional[int]
    days_overdue: int
    
    # Loan tracking
    loan_status: LoanStatus
    renewals_count: int
    last_payment_date: Optional[date]
    is_within_grace_period: bool
    
    # Available actions
    minimum_payment_required: float
    can_extend: bool
    can_redeem: bool
    is_forfeit_eligible: bool

class TransactionSearch(BaseModel):
    """Search parameters for transactions"""
    customer_id: Optional[UUID] = None
    item_id: Optional[UUID] = None
    loan_id: Optional[UUID] = None
    transaction_type: Optional[TransactionType] = None
    status: Optional[TransactionStatus] = None
    loan_status: Optional[LoanStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_overdue: Optional[bool] = None

class StoreScenarioResponse(BaseModel):
    """Response for store scenario testing"""
    scenario_name: str
    description: str
    success: bool
    loan_id: Optional[UUID] = None
    final_balance: Optional[float] = None
    final_status: Optional[str] = None
    transactions_created: List[UUID] = Field(default_factory=list)
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)