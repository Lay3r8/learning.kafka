"""
Query Service - CQRS Read Side

Responsibilities:
- Handle read operations (queries)
- Maintain denormalized read models
- Implement caching for performance
- Provide optimized queries (O(1) lookups)
"""
from logging import basicConfig, getLogger, INFO, StreamHandler
from sys import stdout
from json import loads as json_loads
from os import getenv
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
import redis
from uvicorn import run as uvicorn_run
from models import (
    PlayerStats,
    LeaderboardEntry,
    LeaderboardResponse,
    HealthResponse as BaseHealthResponse,
)


class BetRecord(BaseModel):
    bet_id: str
    event_id: str
    session_id: str | None = None
    game_type: str
    amount: float
    timestamp: int
    status: str
    correlation_id: str | None = None
    profit: float | None = None


class BetListResponse(BaseModel):
    bets: list[BetRecord]


# Configuration from environment (required - no defaults)
REDIS_HOST = getenv("REDIS_HOST")
REDIS_PORT = getenv("REDIS_PORT")

# Validate required configuration
if not REDIS_HOST:
    raise ValueError("REDIS_HOST environment variable is required")
if not REDIS_PORT:
    raise ValueError("REDIS_PORT environment variable is required")

# Convert to int after validation
REDIS_PORT = int(REDIS_PORT)

# Configure logging
basicConfig(
    level=INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[StreamHandler(stdout)]
)
logger = getLogger(__name__)

app = FastAPI(
    title="Query Service",
    description="CQRS Read Side - Handles optimized queries with caching",
    version="1.0.0"
)

# Initialize Redis with connection pooling
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True,
    health_check_interval=30
)

logger.info(
    "Query service initialized",
    extra={
        "redis_host": REDIS_HOST,
        "redis_port": REDIS_PORT
    }
)


# Service-specific models (not shared - only used by Query Service)
class HealthResponse(BaseHealthResponse):
    """Extended health response for Query Service - includes Redis status"""
    redis: str


class PlayerBalanceResponse(BaseModel):
    """Balance-only response for lightweight queries"""
    player_id: str = Field(..., description="Unique player identifier")
    balance: float = Field(..., description="Current balance in dollars")
    last_updated: int = Field(..., description="Last update timestamp in milliseconds")


class SummaryStatsResponse(BaseModel):
    """Aggregate statistics response"""
    total_players: int = Field(..., description="Total number of players")
    total_bets: int = Field(..., description="Total number of bets")
    total_wagered: float = Field(..., description="Total amount wagered")
    active_sessions: int = Field(..., description="Number of active sessions")


@app.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health():
    """Health check endpoint"""
    try:
        redis_client.ping()
        logger.debug("Health check passed")
        return HealthResponse(
            status="healthy",
            service="query-service",
            redis="connected"
        )
    except Exception as e:
        logger.error("Health check failed", extra={"error": str(e)})
        return HealthResponse(
            status="unhealthy",
            service="query-service",
            redis="disconnected"
        )


@app.get("/api/v1/players/{player_id}/balance", response_model=PlayerBalanceResponse)
async def get_player_balance(player_id: str):
    """
    Get player balance (O(1) lookup).

    Args:
        player_id: Unique player identifier

    Returns:
        PlayerBalanceResponse with current balance and timestamp
    """
    try:
        # O(1) Redis lookup
        balance_data = redis_client.get(f"player:{player_id}:balance")

        if not balance_data:
            logger.warning(
                "Player not found",
                extra={"player_id": player_id}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Player not found"
            )

        balance = json_loads(balance_data)

        logger.info(
            "Player balance retrieved",
            extra={
                "player_id": player_id,
                "balance": balance.get("balance")
            }
        )

        return PlayerBalanceResponse(**balance)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to fetch player balance",
            extra={"player_id": player_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve balance"
        )


@app.get("/api/v1/players/{player_id}/stats", response_model=PlayerStats)
async def get_player_stats(player_id: str):
    """
    Get player statistics (O(1) lookup).

    Args:
        player_id: Unique player identifier

    Returns:
        PlayerStats with comprehensive player statistics
    """
    try:
        stats_data = redis_client.get(f"player:{player_id}:stats")

        if not stats_data:
            logger.warning(
                "Player stats not found",
                extra={"player_id": player_id}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Player not found"
            )

        stats = json_loads(stats_data)

        logger.info(
            "Player stats retrieved",
            extra={
                "player_id": player_id,
                "games_played": stats.get("games_played")
            }
        )

        return PlayerStats(**stats)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to fetch player stats",
            extra={"player_id": player_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve stats"
        )


@app.get("/api/v1/players/{player_id}/bets", response_model=BetListResponse)
async def get_player_bets(player_id: str):
    """
    Return the recent bets for a player from Redis (most recent first).
    """
    try:
        key = f"player:{player_id}:bets"
        raw = redis_client.lrange(key, 0, 999)

        bets = []
        for item in raw:
            try:
                obj = json_loads(item)
                bets.append(BetRecord(**obj))
            except Exception:
                continue

        return BetListResponse(bets=bets)
    except Exception as e:
        logger.error("Failed to fetch player bets", extra={"player_id": player_id, "error": str(e)}, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch player bets")


@app.get("/api/v1/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(limit: int = Query(default=10, ge=1, le=100, description="Number of top players to return")):
    """
    Get top players by balance (O(log n) sorted set operation).

    Args:
        limit: Number of top players to return (1-100, default 10)

    Returns:
        LeaderboardResponse with ranked players
    """
    try:
        # O(log n) Redis sorted set operation
        top_players = redis_client.zrevrange(
            "leaderboard:balance",
            0,
            limit - 1,
            withscores=True
        )

        leaderboard = [
            LeaderboardEntry(
                player_id=player_id,
                balance=float(balance),
                rank=idx + 1
            )
            for idx, (player_id, balance) in enumerate(top_players)
        ]

        logger.info(
            "Leaderboard retrieved",
            extra={"limit": limit, "results": len(leaderboard)}
        )

        return LeaderboardResponse(leaderboard=leaderboard)

    except Exception as e:
        logger.error(
            "Failed to fetch leaderboard",
            extra={"error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve leaderboard"
        )


@app.get("/api/v1/stats/summary", response_model=SummaryStatsResponse)
async def get_summary_stats():
    """
    Get global system statistics.
    """
    try:
        summary = SummaryStatsResponse(
            total_players=int(redis_client.get("stats:total_players") or 0),
            total_bets=int(redis_client.get("stats:total_bets") or 0),
            total_wagered=float(redis_client.get("stats:total_wagered") or 0),
            active_sessions=int(redis_client.get("stats:active_sessions") or 0)
        )

        return summary

    except Exception as e:
        print(f"Error fetching summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    uvicorn_run(app, host="0.0.0.0", port=5001)
