from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from beanie import Document
from pydantic import Field
from enum import Enum

class ItemStatus(str, Enum):
    ACTIVE = "active"          # Currently pawned
    REDEEMED = "redeemed"      # Customer bought back
    FORFEITED = "forfeited"    # Became shop property

class Item(Document):
    item_id: UUID = Field(default_factory=uuid4)
    
    # Basic item information - SIMPLIFIED FOR V1
    description: str = Field(..., min_length=1, max_length=500, description="What is this item?")
    serial_number: Optional[str] = Field(None, max_length=100, description="Serial number if available")
    
    # Financial details
    loan_amount: float = Field(..., gt=0, description="Amount loaned for this item")
    storage_location: Optional[str] = Field(None, max_length=100, description="Where is this item stored?")
    
    # Status and ownership
    status: ItemStatus = Field(default=ItemStatus.ACTIVE)
    customer_id: UUID = Field(..., description="Owner of the item")
    
    # Internal notes (NOT shown on customer receipts)
    internal_notes: Optional[str] = Field(None, max_length=1000, description="Internal notes - not visible to customer")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Who processed this item
    created_by: UUID = Field(..., description="Staff member who processed the item")

    def __repr__(self) -> str:
        return f"<Item {self.description[:30]} - {self.status.value}>"

    def __str__(self) -> str:
        return self.description

    @property
    def display_description(self) -> str:
        """Get description for customer receipt (no internal notes)"""
        return self.description

    class Settings:
        name = "items"
        indexes = [
            [("customer_id", 1), ("status", 1)],
            [("status", 1), ("created_at", -1)]
        ]