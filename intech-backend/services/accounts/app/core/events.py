from app.core.logger import logging

logger = logging.getLogger(__name__)


async def publish_event(event_type: str, payload: dict):
    """
    Stub for publishing events to your message broker.
    Replace with Kafka / RabbitMQ / Redis Stream producer.
    """
    logger.info("publish_event %s %s", event_type, payload)
    # TODO: implement actual broker publish (async)
