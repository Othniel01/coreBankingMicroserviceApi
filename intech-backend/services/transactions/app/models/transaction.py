import enum
import uuid
from sqlalchemy import Column, String, Enum, Numeric, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class TransactionStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"


class TransactionType(str, enum.Enum):
    transfer = "transfer"
    deposit = "deposit"
    withdrawal = "withdrawal"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference = Column(String(64), unique=True, index=True, nullable=False)
    sender_user_id = Column(String(64), nullable=False)
    recipient_user_id = Column(String(64), nullable=True)
    amount = Column(Numeric(precision=12, scale=2), nullable=False)
    currency = Column(String(10), nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    status = Column(
        Enum(TransactionStatus), default=TransactionStatus.pending, nullable=False
    )
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    external_bank = Column(String(64), nullable=True)  # For external transfers
    external_reference = Column(String(128), nullable=True)  # Bank/NIBSS reference


class TransactionLimit(Base):
    __tablename__ = "transaction_limits"

    user_id = Column(String(64), primary_key=True)
    daily_limit = Column(Numeric(precision=12, scale=2), nullable=False, default=20000)
