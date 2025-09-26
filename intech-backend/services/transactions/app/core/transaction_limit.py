from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.transaction import Transaction
from app.models.transaction import TransactionLimit


async def get_daily_spent(db: AsyncSession, user_id: str):
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(Transaction.sender_user_id == user_id)
        .where(Transaction.created_at >= today_start)
        .where(Transaction.status == "success")
    )
    return float(result.scalar() or 0)


async def check_transaction_limit(db: AsyncSession, user_id: str, amount: float):
    result = await db.get(TransactionLimit, user_id)
    limit = float(result.daily_limit) if result else 20000
    spent = await get_daily_spent(db, user_id)
    if amount + spent > limit:
        raise ValueError(f"Daily transaction limit exceeded: {spent}/{limit}")
    return True
