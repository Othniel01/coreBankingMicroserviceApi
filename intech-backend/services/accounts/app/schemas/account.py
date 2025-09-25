# app/schemas/account.py
from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional
from datetime import datetime


class AccountCreate(BaseModel):
    external_id: Optional[str] = Field(None, description="External account reference")
    owner_user_id: str
    currency: str = "NGN"


class AccountUpdate(BaseModel):
    currency: Optional[str] = None
    extra_metadata: Optional[str] = None
    is_active: Optional[bool] = None


class AccountOut(BaseModel):
    id: int
    external_id: Optional[str] = None
    owner_user_id: str
    currency: str
    balance: Decimal
    is_frozen: bool
    is_active: bool
    extra_metadata: Optional[str] = None
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True


class BalanceOut(BaseModel):
    external_id: str
    balance: Decimal
    currency: str
