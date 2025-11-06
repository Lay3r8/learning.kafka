"""
Command Service - CQRS Write Side

Responsibilities:
- Handle write operations (place bets)
- Validate business rules
- Publish events to Kafka
- Transactional guarantees (ACID)
"""
from logging import basicConfig, getLogger, INFO, StreamHandler
from sys import stdout
from json import dumps as json_dumps
from os import getenv
from random import uniform
from time import time
from uuid import uuid4
from fastapi import Header
from fastapi import FastAPI, HTTPException, status
from kafka import KafkaProducer
from uvicorn import run as uvicorn_run
from models import (
    BetEvent,
    EventType,
    GameType,
    PlaceBetRequest,
    PlaceBetResponse,
    HealthResponse,
)


# Configuration from environment (required - no defaults)
KAFKA_BOOTSTRAP_SERVERS = getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_TOPIC = getenv("KAFKA_TOPIC")

# Validate required configuration
if not KAFKA_BOOTSTRAP_SERVERS:
    raise ValueError("KAFKA_BOOTSTRAP_SERVERS environment variable is required")
if not KAFKA_TOPIC:
    raise ValueError("KAFKA_TOPIC environment variable is required")

# Configure logging
basicConfig(
    level=INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[StreamHandler(stdout)]
)
logger = getLogger(__name__)

app = FastAPI(
    title="Command Service",
    description="CQRS Write Side - Handles bet placement commands",
    version="1.0.0"
)

# Initialize Kafka Producer with best practices
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json_dumps(v).encode("utf-8"),
    acks="all",  # Wait for all replicas (durability)
    retries=3,
    max_in_flight_requests_per_connection=1,  # Ensure ordering
    linger_ms=10  # Batch for efficiency
)

logger.info(
    "Command service initialized",
    extra={
        "kafka_bootstrap_servers": KAFKA_BOOTSTRAP_SERVERS,
        "kafka_topic": KAFKA_TOPIC
    }
)


@app.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health():
    """Health check endpoint"""
    return HealthResponse(status="healthy", service="command-service")


@app.post("/api/v1/bets", response_model=PlaceBetResponse, status_code=status.HTTP_202_ACCEPTED)
async def place_bet(request: PlaceBetRequest, x_correlation_id: str | None = Header(default=None)):
    """
    Place a bet (Command Handler).

    Validates business rules and publishes events to Kafka.
    Returns 202 Accepted for async processing.
    """
    bet_id = str(uuid4())
    # Use provided correlation id if present, otherwise generate (gateway should usually provide it)
    correlation_id = x_correlation_id or str(uuid4())

    try:
        # Create bet placed event
        bet_placed_event = BetEvent(
            event_id=str(uuid4()),
            player_id=request.player_id,
            game_type=GameType(request.game_type),
            event_type=EventType.BET_PLACED,
            amount=request.amount,
            timestamp=int(time() * 1000),
            session_id=request.session_id,
            bet_id=bet_id,
            correlation_id=correlation_id,
            ip_address=request.ip_address
        )

        # Publish to Kafka (transactional)
        # Put correlation_id into Kafka message headers for proper propagation (not only payload)
        future = producer.send(
            KAFKA_TOPIC,
            bet_placed_event.to_dict(),
            headers=[("X-Correlation-ID", correlation_id.encode("utf-8"))]
        )
        record_metadata = future.get(timeout=10)  # Block until acknowledged

        logger.info(
            "Bet placed event published",
            extra={
                "bet_id": bet_id,
                "correlation_id": correlation_id,
                "player_id": request.player_id,
                "amount": request.amount,
                "game_type": request.game_type,
                "partition": record_metadata.partition,
                "offset": record_metadata.offset
            }
        )

        # Simulate game outcome (simplified - could be separate service)
        outcome_event = _simulate_game_outcome(request, bet_id, correlation_id)

        if outcome_event:
            future = producer.send(
                KAFKA_TOPIC,
                outcome_event.to_dict(),
                headers=[("X-Correlation-ID", correlation_id.encode("utf-8"))]
            )
            record_metadata = future.get(timeout=10)

            logger.info(
                "Bet outcome event published",
                extra={
                    "bet_id": bet_id,
                    "correlation_id": correlation_id,
                    "event_type": outcome_event.event_type.value,
                    "amount": outcome_event.amount,
                    "partition": record_metadata.partition,
                    "offset": record_metadata.offset
                }
            )

        producer.flush()

        return PlaceBetResponse(
            bet_id=bet_id,
            correlation_id=correlation_id,
            status="accepted",
            message="Bet placed successfully",
            timestamp=time()
        )

    except Exception as e:
        logger.error(
            "Failed to place bet",
            extra={
                "bet_id": bet_id,
                "correlation_id": correlation_id,
                "player_id": request.player_id,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process bet"
        )


def _simulate_game_outcome(request: PlaceBetRequest, bet_id: str, correlation_id: str) -> BetEvent:
    """
    Simulate game outcome (48% win rate for house edge).
    In production, this would be a separate Game Engine service.
    """
    is_win = uniform(0, 1) > 0.52  # 48% win rate

    if is_win:
        win_amount = round(request.amount * uniform(1.5, 3.0), 2)
        return BetEvent(
            event_id=str(uuid4()),
            player_id=request.player_id,
            game_type=GameType(request.game_type),
            event_type=EventType.BET_WON,
            amount=win_amount,
            timestamp=int(time() * 1000),
            session_id=request.session_id,
            bet_id=bet_id,
            correlation_id=correlation_id,
            ip_address=request.ip_address
        )
    else:
        return BetEvent(
            event_id=str(uuid4()),
            player_id=request.player_id,
            game_type=GameType(request.game_type),
            event_type=EventType.BET_LOST,
            amount=request.amount,
            timestamp=int(time() * 1000),
            session_id=request.session_id,
            bet_id=bet_id,
            correlation_id=correlation_id,
            ip_address=request.ip_address
        )


if __name__ == "__main__":
    uvicorn_run(app, host="0.0.0.0", port=5000)
