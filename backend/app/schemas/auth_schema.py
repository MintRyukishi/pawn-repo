from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str 

class TokenPayLoad(BaseModel):
    sub: UUID = None
    exp: int = None