import uuid
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, func
from app.db.db import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)

    external_id = Column(
        String,
        unique=True,
        nullable=False,
        default=lambda: f"ACC-{uuid.uuid4().hex[:8]}",
    )

    owner_user_id = Column(String(64), index=True, nullable=False)

    account_number = Column(String(10), unique=True, nullable=False)

    hashed_pin = Column(String(128), nullable=False)

    currency = Column(String(8), nullable=False, default="NGN")

    balance = Column(Numeric(18, 2), nullable=False, default=0)

    is_frozen = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    extra_metadata = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )
