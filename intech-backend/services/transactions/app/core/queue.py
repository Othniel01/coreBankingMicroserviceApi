import json
from aio_pika import connect_robust, Message, DeliveryMode
from app.core.config import settings

_connection = None
_channel = None


async def get_channel():
    """
    Get a persistent RabbitMQ channel.
    """
    global _connection, _channel
    if _channel and not _channel.is_closed:
        return _channel

    _connection = await connect_robust(settings.RABBITMQ_URL)
    _channel = await _connection.channel()
    return _channel


async def publish_message(queue: str, message: dict):
    """
    Publish a message to the specified queue.
    """
    channel = await get_channel()
    await channel.declare_queue(queue, durable=True)

    msg = Message(
        body=json.dumps(message).encode("utf-8"),
        delivery_mode=DeliveryMode.PERSISTENT,
    )
    await channel.default_exchange.publish(msg, routing_key=queue)


# Convenience wrappers for standard queues
async def publish_transaction_message(message: dict):
    await publish_message(settings.RABBITMQ_QUEUE_TRANSACTIONS, message)


async def publish_settlement_message(message: dict):
    await publish_message(settings.RABBITMQ_QUEUE_SETTLEMENT, message)


async def publish_fraud_message(message: dict):
    await publish_message(settings.RABBITMQ_QUEUE_FRAUD, message)
