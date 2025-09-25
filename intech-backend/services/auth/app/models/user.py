# app/models.py
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime, timezone
from app.db.db import Base


class User(Base):
    __tablename__ = "users"
    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = sa.Column(sa.String(255), unique=True, nullable=False, index=True)
    hashed_password = sa.Column(sa.String(512), nullable=False)
    full_name = sa.Column(sa.String(255), nullable=True)
    is_active = sa.Column(sa.Boolean, default=True)
    is_superuser = sa.Column(sa.Boolean, default=False)
    created_at = sa.Column(
        sa.DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False
    )
    updated_at = sa.Column(
        sa.DateTime(timezone=True), onupdate=datetime.now(timezone.utc)
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = sa.Column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = sa.Column(sa.String(128), nullable=False, index=True)
    revoked = sa.Column(sa.Boolean, default=False)
    created_at = sa.Column(
        sa.DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False
    )
    expires_at = sa.Column(sa.DateTime(timezone=True), nullable=False)
    meta = sa.Column(JSONB, nullable=True)
