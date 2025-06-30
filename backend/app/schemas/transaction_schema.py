# backend/app/schemas/transaction_schema.py
from uuid import UUID
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
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

class RenewalTransactionCreate(BaseModel):
    """Process a standard renewal payment (backwards compatible)"""
    loan_id: UUID = Field(..., description="Original pawn transaction ID")
    renewal_fee: float = Field(..., gt=0, description="Interest fee amount")
    payment_method: PaymentMethod = Field(default=PaymentMethod.CASH)
    notes: Optional[str] = Field(None, max_length=1000)

class RedemptionTransactionCreate(BaseModel):
    """Process full redemption (principal + interest)"""
    loan_id: UUID = Field(..., description="Original pawn transaction ID")
    total_payment: float = Field(..., gt=0, description="Total payment amount")
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

class ReceiptScheduleItem(BaseModel):
    """Single month in the 3-month receipt schedule"""
    month: int = Field(..., ge=1, le=3, description="Month number (1-3)")
    due_date: str = Field(..., description="Formatted due date")
    due_date_raw: date = Field(..., description="Raw due date for calculations")
    interest_fee: float = Field(..., ge=0, description="Monthly interest fee")
    principal_due: float = Field(..., ge=0, description="Principal amount (only for redemption)")
    total_due: float = Field(..., ge=0, description="Total amount due this month")
    payment_type: str = Field(..., description="Type of payment (Interest Only / Full Redemption)")
    is_redemption_option: bool = Field(..., description="Whether this includes redemption option")

class LoanReceiptOut(BaseModel):
    """Receipt information for customer"""
    # Loan summary
    loan_id: UUID
    receipt_number: Optional[str]
    transaction_date: datetime
    
    # Customer and item
    customer_name: str
    customer_phone: str
    item_description: str
    
    # Financial summary
    original_loan_amount: float
    current_balance: float
    monthly_interest_fee: float
    total_interest_paid: float = Field(..., description="Total interest paid to date")
    
    # Current status
    current_due_date: date
    days_until_due: Optional[int]
    renewals_count: int
    loan_status: LoanStatus
    
    # 3-month payment schedule
    payment_schedule: List[ReceiptScheduleItem]
    
    # Important dates
    final_forfeit_date: date
    
    # Footer notes
    receipt_notes: List[str] = Field(default_factory=lambda: [
        "Minimum payment to extend: Monthly interest fee",
        "Extensions calculated from original due date", 
        "Late fee applies after 1 week grace period",
        "Item forfeited after 3 months + 2 week grace period",
        "Cash payments only"
    ])

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
    details: Dict[str, Any] = Field(default_factory=dict)# backend/app/schemas/transaction_schema.py
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
    monthly_renewal_fee: float = Field(..., gt=0, description="Monthly renewal fee (e.g., $20)")
    additional_fees: Optional[float] = Field(default=0.0, ge=0)

class FlexibleRenewalCreate(BaseModel):
    """Process a flexible renewal payment with custom amount and date"""
    loan_id: UUID = Field(..., description="Original pawn transaction ID")
    payment_amount: float = Field(..., gt=0, description="Amount paid (can be partial or multiple months)")
    payment_date: date = Field(..., description="Date when payment was made")
    payment_method: PaymentMethod = Field(default=PaymentMethod.CASH)
    notes: Optional[str] = Field(None, max_length=1000)

class RenewalTransactionCreate(BaseModel):
    """Process a standard renewal payment (backwards compatible)"""
    loan_id: UUID = Field(..., description="Original pawn transaction ID")
    renewal_fee: float = Field(..., gt=0, description="Renewal fee amount")
    payment_method: PaymentMethod = Field(default=PaymentMethod.CASH)
    notes: Optional[str] = Field(None, max_length=1000)

class RedemptionTransactionCreate(BaseModel):
    """Process full redemption (principal + interest)"""
    loan_id: UUID = Field(..., description="Original pawn transaction ID")
    total_payment: float = Field(..., gt=0, description="Total payment amount")
    payment_method: PaymentMethod = Field(default=PaymentMethod.CASH)
    notes: Optional[str] = Field(None, max_length=1000)

class TransactionUpdate(BaseModel):
    status: Optional[TransactionStatus] = None
    payment_method: Optional[PaymentMethod] = None
    notes: Optional[str] = Field(None, max_length=1000)

class ReceiptScheduleItem(BaseModel):
    """Single month in the 3-month receipt schedule"""
    month: int = Field(..., ge=1, le=3, description="Month number (1-3)")
    due_date: str = Field(..., description="Formatted due date")
    due_date_raw: date = Field(..., description="Raw due date for calculations")
    renewal_fee: float = Field(..., ge=0, description="Monthly renewal fee")
    principal_due: float = Field(..., ge=0, description="Principal amount (only for redemption)")
    total_due: float = Field(..., ge=0, description="Total amount due this month")
    payment_type: str = Field(..., description="Type of payment (Renewal Only / Full Redemption)")
    is_redemption_option: bool = Field(..., description="Whether this includes redemption option")

class PaymentAllocationOut(BaseModel):
    """Details of how a renewal payment is allocated"""
    months_covered: int = Field(..., description="Full months covered by payment")
    partial_month_ratio: float = Field(..., ge=0, le=1, description="Partial month coverage (0.0 to 1.0)")
    next_due_date: date = Field(..., description="When next payment is due")
    payment_status: str = Field(..., description="'advance', 'on_time', or 'late'")
    extension_days: int = Field(..., description="Days the loan is extended")
    amount_per_month: float = Field(..., description="Monthly renewal fee")
    total_months_paid: float = Field(..., description="Total months covered (including partial)")

class TransactionOut(TransactionBase):
    """Extended transaction output with payment allocation details"""
    payment_allocation: PaymentAllocationOut
    original_due_date: date = Field(..., description="Due date before this payment")
    new_due_date: date = Field(..., description="Due date after this payment")
    transaction_id: UUID
    status: TransactionStatus
    
    # Financial details
    principal_amount: Optional[float]
    interest_amount: Optional[float]
    additional_fees: float
    
    # Payment details
    payment_method: PaymentMethod
    
    # References
    customer_id: UUID
    item_id: Optional[UUID]
    loan_id: Optional[UUID]
    
    # Loan details (for pawn transactions)
    loan_status: Optional[LoanStatus]
    monthly_renewal_fee: Optional[float]
    
    # Dates
    transaction_date: datetime
    original_due_date: Optional[date]
    current_due_date: Optional[date]
    final_forfeit_date: Optional[date]
    
    # Renewal tracking
    renewals_count: int
    last_renewal_date: Optional[date]
    months_without_payment: int
    
    # Computed fields
    is_loan_active: bool
    days_until_due: Optional[int]
    is_overdue: bool
    days_overdue: int
    
    # Receipt and audit
    receipt_number: Optional[str]
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class LoanReceiptOut(BaseModel):
    """Receipt information for customer"""
    # Loan summary
    loan_id: UUID
    receipt_number: Optional[str]
    transaction_date: datetime
    
    # Customer and item
    customer_name: str
    customer_phone: str
    item_description: str
    
    # Financial summary
    principal_amount: float
    monthly_renewal_fee: float
    total_interest_paid: float = Field(..., description="Total interest paid to date")
    
    # Current status
    current_due_date: date
    days_until_due: Optional[int]
    renewals_count: int
    loan_status: LoanStatus
    
    # 3-month payment schedule
    payment_schedule: List[ReceiptScheduleItem]
    
    # Important dates
    final_forfeit_date: date
    
    # Footer notes
    receipt_notes: List[str] = Field(default_factory=lambda: [
        "Item will be forfeited if no payment is made for 3 consecutive months",
        "Renewal payments extend loan by 1 month from current due date", 
        "Principal + interest must be paid to redeem item",
        "All payments are non-refundable"
    ])

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

class LoanSummary(BaseModel):
    """Summary of loan information"""
    loan_id: UUID
    customer_name: str
    customer_phone: str
    item_description: str
    principal_amount: float
    monthly_renewal_fee: float
    current_due_date: date
    days_until_due: Optional[int]
    days_overdue: int
    renewals_count: int
    loan_status: LoanStatus
    total_interest_paid: float
    final_forfeit_date: date

class DueLoansSummary(BaseModel):
    """Summary of loans due in specified timeframe"""
    loans_due_soon: List[LoanSummary]
    overdue_loans: List[LoanSummary]
    forfeit_eligible_loans: List[LoanSummary]
    total_loans: int
    total_principal_at_risk: float
    total_overdue_interest: float