# backend/app/schemas/customer_schema.py
from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.models.customer_model import CustomerStatus

class CustomerBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    phone: str = Field(..., min_length=10, max_length=15)
    email: Optional[EmailStr] = None
    notes: Optional[str] = Field(None, max_length=1000, description="Optional notes about the customer")

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone: Optional[str] = Field(None, min_length=10, max_length=15)
    email: Optional[EmailStr] = None
    notes: Optional[str] = Field(None, max_length=1000, description="Optional notes about the customer")
    is_active: Optional[bool] = None  # Keep for backward compatibility

class CustomerStatusUpdate(BaseModel):
    status: CustomerStatus
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for status change")
    suspension_until: Optional[datetime] = Field(None, description="When suspension ends (required for suspended status)")

class CustomerOut(CustomerBase):
    customer_id: UUID
    status: CustomerStatus
    status_reason: Optional[str]
    status_changed_at: Optional[datetime]
    suspension_until: Optional[datetime]
    is_active: bool  # Keep for backward compatibility
    can_transact: bool
    is_suspended_temporarily: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CustomerSearch(BaseModel):
    query: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[CustomerStatus] = None
    is_active: Optional[bool] = True