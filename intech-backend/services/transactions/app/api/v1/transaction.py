from typing import List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.db import get_db
from app.core.jwks import get_current_user, require_superuser
from app.core.transaction import create_transaction, update_transaction_status
from app.schemas.transaction import TransactionCreate, TransactionOut
from app.models.transaction import (
    Transaction,
    TransactionLimit,
    TransactionStatus,
    TransactionType,
)
from app.core.queue import publish_message
from app.core.rate_limiter import rate_limit_dependency
from app.core.transaction_limit import check_transaction_limit
from app.core.logger import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/transactions", tags=["transactions"])


def rate_limit_dep(
    request: Request, user=Depends(get_current_user), limit: int = 60, period: int = 60
):
    return rate_limit_dependency(
        request, user_id=user["sub"], limit=limit, period=period
    )


@router.post(
    "",
    response_model=TransactionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_dep)],
)
async def initiate_transaction(
    payload: TransactionCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):

    try:
        await check_transaction_limit(db, user["sub"], float(payload.amount))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    txn = await create_transaction(db, user["sub"], payload)
    logger.info(f"Transaction initiated: {txn.reference} by user {user['sub']}")

    await publish_message(
        queue="fraud_queue",
        message={
            "transaction_id": str(txn.id),
            "sender_user_id": txn.sender_user_id,
            "recipient_user_id": txn.recipient_user_id,
            "amount": str(txn.amount),
            "currency": txn.currency,
            "type": txn.type.value,
        },
    )

    if txn.external_bank:
        await publish_message(
            queue="settlement_queue",
            message={
                "transaction_id": str(txn.id),
                "external_bank": txn.external_bank,
                "recipient_user_id": txn.recipient_user_id,
                "amount": str(txn.amount),
                "currency": txn.currency,
            },
        )

    return txn


@router.get(
    "", response_model=List[TransactionOut], dependencies=[Depends(rate_limit_dep)]
)
async def list_transactions(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    type: Optional[TransactionType] = None,
    status: Optional[TransactionStatus] = None,
):
    query = "SELECT * FROM transactions WHERE sender_user_id = :user_id OR recipient_user_id = :user_id"
    params = {"user_id": user["sub"]}

    if type:
        query += " AND type = :type"
        params["type"] = type.value
    if status:
        query += " AND status = :status"
        params["status"] = status.value

    result = await db.execute(query, params)
    transactions = result.fetchall()
    logger.info(f"{len(transactions)} transactions listed for user {user['sub']}")
    return transactions


@router.get(
    "/{txn_id}", response_model=TransactionOut, dependencies=[Depends(rate_limit_dep)]
)
async def get_transaction(
    txn_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)
):
    txn = await db.get(Transaction, txn_id)
    if not txn:
        logger.warning(f"Transaction {txn_id} not found for user {user['sub']}")
        raise HTTPException(status_code=404, detail="Transaction not found")
    if txn.sender_user_id != user["sub"] and txn.recipient_user_id != user["sub"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    logger.info(f"Transaction {txn_id} fetched for user {user['sub']}")
    return txn


@router.patch(
    "/{txn_id}/status",
    response_model=TransactionOut,
    dependencies=[Depends(rate_limit_dep)],
)
async def patch_transaction_status(
    txn_id: str,
    status: TransactionStatus,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_superuser),
):
    txn = await update_transaction_status(db, txn_id, status)
    if not txn:
        logger.warning(f"Transaction {txn_id} status update failed")
        raise HTTPException(status_code=404, detail="Transaction not found")
    logger.info(f"Transaction {txn_id} status updated to {status}")
    return txn


@router.post(
    "/{txn_id}/approve",
    response_model=TransactionOut,
    dependencies=[Depends(rate_limit_dep)],
)
async def approve_transaction(
    txn_id: str, db: AsyncSession = Depends(get_db), user=Depends(require_superuser)
):
    txn = await update_transaction_status(db, txn_id, TransactionStatus.success)
    if not txn:
        logger.warning(f"Transaction {txn_id} approval failed")
        raise HTTPException(status_code=404, detail="Transaction not found")
    logger.info(f"Transaction {txn_id} approved by superuser")
    return txn


@router.post(
    "/{txn_id}/flag",
    response_model=TransactionOut,
    dependencies=[Depends(rate_limit_dep)],
)
async def flag_transaction(
    txn_id: str, db: AsyncSession = Depends(get_db), user=Depends(require_superuser)
):
    txn = await update_transaction_status(db, txn_id, TransactionStatus.pending)
    if not txn:
        logger.warning(f"Transaction {txn_id} flag failed")
        raise HTTPException(status_code=404, detail="Transaction not found")

    await publish_message(
        queue="fraud_review_queue",
        message={"transaction_id": str(txn.id)},
    )
    logger.info(f"Transaction {txn_id} flagged for review")
    return txn


@router.get(
    "/{txn_id}/settlement",
    response_model=TransactionOut,
    dependencies=[Depends(rate_limit_dep)],
)
async def check_settlement_status(
    txn_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)
):
    txn = await db.get(Transaction, txn_id)
    if not txn:
        logger.warning(f"Settlement check failed for transaction {txn_id}")
        raise HTTPException(status_code=404, detail="Transaction not found")
    if txn.sender_user_id != user["sub"] and txn.recipient_user_id != user["sub"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    logger.info(f"Settlement status fetched for transaction {txn_id}")
    return txn


@router.post("/limits/{user_id}", dependencies=[Depends(require_superuser)])
async def set_daily_limit(
    user_id: str,
    daily_limit: float = Body(..., gt=19999),
    db: AsyncSession = Depends(get_db),
):
    """
    Set a user's daily transaction limit. Must be >= 20,000.
    """
    if daily_limit < 20000:
        raise HTTPException(status_code=400, detail="Minimum daily limit is 20,000")
    limit = await db.get(TransactionLimit, user_id)
    if not limit:
        limit = TransactionLimit(user_id=user_id, daily_limit=daily_limit)
        db.add(limit)
    else:
        limit.daily_limit = daily_limit
    await db.commit()
    await db.refresh(limit)
    logger.info(f"Daily transaction limit set for {user_id}: {daily_limit}")
    return {"user_id": user_id, "daily_limit": daily_limit}
