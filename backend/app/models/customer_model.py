# backend/app/models/customer_model.py
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from beanie import Document, Indexed
from pydantic import Field, EmailStr
from enum import Enum

class CustomerStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"  # Temporarily banned
    BANNED = "banned"        # Permanently banned
    RESTRICTED = "restricted" # Limited transactions only

class Customer(Document):
    customer_id: UUID = Field(default_factory=uuid4)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    phone: Indexed(str, unique=True) = Field(..., min_length=10, max_length=15)
    email: Optional[EmailStr] = None
    notes: Optional[str] = Field(None, max_length=1000, description="Optional notes about the customer")
    
    # Enhanced status system
    status: CustomerStatus = Field(default=CustomerStatus.ACTIVE)
    status_reason: Optional[str] = Field(None, max_length=500, description="Reason for status change")
    status_changed_at: Optional[datetime] = None
    status_changed_by: Optional[UUID] = None  # User ID who changed the status
    suspension_until: Optional[datetime] = Field(None, description="When suspension ends (for temporary bans)")
    
    # Keep is_active for backward compatibility
    is_active: bool = Field(default=True, description="Deprecated - use status instead")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Customer {self.first_name} {self.last_name} - {self.status.value}>"

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def can_transact(self) -> bool:
        """Check if customer can make new transactions"""
        if self.status == CustomerStatus.ACTIVE:
            return True
        elif self.status == CustomerStatus.SUSPENDED:
            # Check if suspension has expired
            if self.suspension_until and datetime.utcnow() > self.suspension_until:
                return True
            return False
        elif self.status in [CustomerStatus.BANNED, CustomerStatus.RESTRICTED]:
            return False
        return False

    @property
    def is_suspended_temporarily(self) -> bool:
        """Check if customer is temporarily suspended"""
        return (
            self.status == CustomerStatus.SUSPENDED and 
            self.suspension_until and 
            datetime.utcnow() < self.suspension_until
        )

    class Settings:
        name = "customers"