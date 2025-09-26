from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from uuid import UUID
from app.models.transaction import TransactionStatus, TransactionType
from datetime import datetime


class TransactionCreate(BaseModel):
    recipient_user_id: Optional[str] = None
    amount: Decimal
    currency: str
    type: TransactionType
    external_bank: Optional[str] = None


class TransactionOut(BaseModel):
    id: UUID
    reference: str
    sender_user_id: str
    recipient_user_id: Optional[str]
    amount: Decimal
    currency: str
    type: TransactionType
    status: TransactionStatus
    created_at: datetime
    updated_at: datetime
    external_bank: Optional[str]
    external_reference: Optional[str]

    class Config:
        orm_mode = True
