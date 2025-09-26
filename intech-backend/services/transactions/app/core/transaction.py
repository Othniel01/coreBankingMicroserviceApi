import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transaction import Transaction, TransactionStatus


async def create_transaction(
    db: AsyncSession, sender_user_id: str, payload
) -> Transaction:
    txn = Transaction(
        reference=str(uuid.uuid4()),
        sender_user_id=sender_user_id,
        recipient_user_id=payload.recipient_user_id,
        amount=payload.amount,
        currency=payload.currency,
        type=payload.type,
        status=TransactionStatus.pending,
        external_bank=payload.external_bank,
    )
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    return txn


async def update_transaction_status(
    db: AsyncSession,
    txn_id: str,
    status: TransactionStatus,
    external_reference: str = None,
):
    txn = await db.get(Transaction, txn_id)
    if not txn:
        return None
    txn.status = status
    txn.updated_at = datetime.now(timezone.utc)
    if external_reference:
        txn.external_reference = external_reference
    await db.commit()
    await db.refresh(txn)
    return txn
