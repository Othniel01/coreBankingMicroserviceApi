import asyncio
import json
import logging
from aio_pika import IncomingMessage
from app.core.config import settings
from app.db.db import get_db
from app.core.transaction import update_transaction_status
from app.models.transaction import TransactionStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fraud_consumer")

RABBITMQ_QUEUE = settings.RABBITMQ_QUEUE_FRAUD


async def handle_fraud_message(message: IncomingMessage):
    async with message.process():
        try:
            data = json.loads(message.body.decode())
            txn_id = data.get("transaction_id")
            amount = float(data.get("amount", 0))

            status = (
                TransactionStatus.pending
                if amount > 1_000_000
                else TransactionStatus.success
            )

            async for db in get_db():
                txn = await update_transaction_status(db, txn_id, status)
                if txn:
                    logger.info(f"Fraud check completed for txn {txn_id}: {status}")
        except Exception as e:
            logger.exception("Failed to process fraud message: %s", e)
