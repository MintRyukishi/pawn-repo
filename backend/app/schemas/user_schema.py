# backend/app/schemas/user_schema.py
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserAuth(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username for the user")
    password: str = Field(..., min_length=8, max_length=128, description="User's password")

class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    disabled: Optional[bool] = None

class UserOut(BaseModel):
    user_id: UUID
    email: EmailStr
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    disabled: Optional[bool] = False

    class Config:
        from_attributes = True