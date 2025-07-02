# backend/app/schemas/item_schema.py - FIXED FOR COPY-PASTE
from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.item_model import ItemStatus

class ItemBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=500, description="What is this item?")
    serial_number: Optional[str] = Field(None, max_length=100, description="Serial number if available")
    loan_amount: float = Field(..., gt=0, description="Amount loaned for this item")
    internal_notes: Optional[str] = Field(None, max_length=1000, description="Internal notes - not visible to customer")

class ItemCreate(ItemBase):
    customer_id: UUID = Field(..., description="Customer who owns this item")

class ItemUpdate(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    serial_number: Optional[str] = Field(None, max_length=100)
    loan_amount: Optional[float] = Field(None, gt=0)
    status: Optional[ItemStatus] = None
    internal_notes: Optional[str] = Field(None, max_length=1000)

class ItemOut(ItemBase):
    item_id: UUID
    status: ItemStatus
    customer_id: UUID
    display_description: str
    created_at: datetime
    updated_at: datetime
    created_by: UUID

    class Config:
        from_attributes = True

class ItemSearch(BaseModel):
    description: Optional[str] = None
    status: Optional[ItemStatus] = None
    customer_id: Optional[UUID] = None
    serial_number: Optional[str] = None

# For customer receipts - excludes internal notes
class ItemReceipt(BaseModel):
    description: str
    serial_number: Optional[str]
    loan_amount: float
    
    class Config:
        from_attributes = True