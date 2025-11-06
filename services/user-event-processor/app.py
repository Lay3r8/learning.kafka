"""
User Event Processor - Consumes user-events from Kafka

Responsibilities:
- Consume USER_REGISTERED, USER_UPDATED, USER_DELETED events
- Update Redis cache for fast user/wallet lookups
- Maintain denormalized read models
- Separate from betting event processor (different bounded context)
"""
from logging import basicConfig, getLogger, INFO, StreamHandler
from sys import stdout
from os import getenv
import json
from kafka import KafkaConsumer
from redis import Redis


# Environment Configuration
KAFKA_BOOTSTRAP_SERVERS = getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9093")
KAFKA_USER_TOPIC = getenv("KAFKA_USER_TOPIC", "user-events")
KAFKA_USER_GROUP_ID = getenv("KAFKA_USER_GROUP_ID", "user-event-processor")
REDIS_HOST = getenv("REDIS_HOST", "redis")
REDIS_PORT = int(getenv("REDIS_PORT", "6379"))

# Logging
basicConfig(
    level=INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[StreamHandler(stdout)]
)
logger = getLogger(__name__)

# Redis Connection
redis_client = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    decode_responses=True
)

logger.info("User Event Processor starting...")
logger.info(f"Kafka Bootstrap Servers: {KAFKA_BOOTSTRAP_SERVERS}")
logger.info(f"Kafka Topic: {KAFKA_USER_TOPIC}")
logger.info(f"Consumer Group: {KAFKA_USER_GROUP_ID}")
logger.info(f"Redis: {REDIS_HOST}:{REDIS_PORT}")


def process_user_registered(event: dict):
    """
    Process USER_REGISTERED event

    Store user info in Redis for fast lookups:
    - user:{user_id}:info -> User details
    - user:{user_id}:wallet -> Wallet balance (cached from PostgreSQL)
    """
    user_id = event.get("user_id")
    data = event.get("data", {})

    try:
        # Store user info
        user_key = f"user:{user_id}:info"
        redis_client.hset(user_key, mapping={
            "email": data.get("email"),
            "username": data.get("username"),
            "is_active": "true",
            "created_at": event.get("timestamp")
        })

        # Initialize wallet cache (balance = 0 for new users)
        wallet_key = f"user:{user_id}:wallet"
        redis_client.hset(wallet_key, mapping={
            "balance": "0.00",
            "currency": "USD",
            "wallet_id": str(data.get("wallet_id"))
        })

        logger.info(
            f"USER_REGISTERED processed: {user_id}",
            extra={
                "user_id": user_id,
                "email": data.get("email"),
                "event_id": event.get("event_id")
            }
        )
    except Exception as e:
        logger.error(f"Failed to process USER_REGISTERED: {e}", exc_info=True)
        raise


def process_user_updated(event: dict):
    """
    Process USER_UPDATED event

    Update user info in Redis cache
    """
    user_id = event.get("user_id")
    data = event.get("data", {})

    try:
        user_key = f"user:{user_id}:info"

        # Update fields that changed
        updates = {}
        if "email" in data:
            updates["email"] = data["email"]
        if "username" in data:
            updates["username"] = data["username"]

        if updates:
            redis_client.hset(user_key, mapping=updates)
            logger.info(f"USER_UPDATED processed: {user_id}", extra={"updates": updates})
    except Exception as e:
        logger.error(f"Failed to process USER_UPDATED: {e}", exc_info=True)
        raise


def process_user_deleted(event: dict):
    """
    Process USER_DELETED event

    Mark user as inactive in Redis (soft delete)
    """
    user_id = event.get("user_id")

    try:
        user_key = f"user:{user_id}:info"
        redis_client.hset(user_key, "is_active", "false")

        logger.info(f"USER_DELETED processed: {user_id}")
    except Exception as e:
        logger.error(f"Failed to process USER_DELETED: {e}", exc_info=True)
        raise


def process_event(event: dict):
    """Route event to appropriate handler"""
    event_type = event.get("event_type")

    handlers = {
        "USER_REGISTERED": process_user_registered,
        "USER_UPDATED": process_user_updated,
        "USER_DELETED": process_user_deleted,
    }

    handler = handlers.get(event_type)
    if handler:
        handler(event)
    else:
        logger.warning(f"Unknown event type: {event_type}")


def main():
    """Main consumer loop"""
    logger.info("Initializing Kafka consumer...")

    consumer = KafkaConsumer(
        KAFKA_USER_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_USER_GROUP_ID,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    )

    logger.info(f"Consumer subscribed to topic: {KAFKA_USER_TOPIC}")
    logger.info("Waiting for user events...")

    try:
        for message in consumer:
            try:
                event = message.value

                logger.info(
                    f"Event received: {event.get('event_type')}",
                    extra={
                        "event_id": event.get("event_id"),
                        "user_id": event.get("user_id"),
                        "partition": message.partition,
                        "offset": message.offset
                    }
                )

                # Extract correlation ID from headers
                correlation_id = None
                if message.headers:
                    for key, value in message.headers:
                        if key == "X-Correlation-ID":
                            correlation_id = value.decode("utf-8")
                            break

                if not correlation_id:
                    correlation_id = event.get("correlation_id")

                logger.info(f"Processing with correlation_id: {correlation_id}")

                # Process the event
                process_event(event)

            except Exception as e:
                logger.error(
                    f"Error processing message: {e}",
                    exc_info=True,
                    extra={
                        "partition": message.partition,
                        "offset": message.offset
                    }
                )
                # Continue processing other messages
                continue

    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    finally:
        consumer.close()
        logger.info("Consumer closed")


if __name__ == "__main__":
    main()
