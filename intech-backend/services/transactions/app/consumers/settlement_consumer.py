import asyncio
import json
import logging
from aio_pika import connect_robust, IncomingMessage
from app.core.config import settings
from app.db.db import get_db
from app.core.transaction import update_transaction_status
from app.models.transaction import TransactionStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("settlement_consumer")

RABBITMQ_QUEUE = settings.RABBITMQ_QUEUE_SETTLEMENT


async def handle_settlement_message(message: IncomingMessage):
    async with message.process():
        try:
            data = json.loads(message.body.decode())
            txn_id = data.get("transaction_id")
            external_bank = data.get("external_bank")

            logger.info(f"Processing settlement for txn {txn_id} to {external_bank}")

            settlement_success = True  # TODO: Replace with real bank connector API call
            status = (
                TransactionStatus.success
                if settlement_success
                else TransactionStatus.failed
            )
            external_ref = f"{external_bank}-{txn_id}"

            async for db in get_db():
                txn = await update_transaction_status(
                    db, txn_id, status, external_reference=external_ref
                )
                if txn:
                    logger.info(f"Settlement completed for txn {txn_id}: {status}")
        except Exception as e:
            logger.exception("Failed to process settlement message: %s", e)
