"""
Shared data models for CQRS gaming system.
Used across all microservices for consistency.

Includes:
- Domain Models: Events, Commands, Snapshots (Event Sourcing/CQRS)
- API Contracts: Request/Response DTOs shared across services
- Enums: Shared enumeration types
"""
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class EventType(Enum):
    """Event types in the gaming system"""
    BET_PLACED = "bet_placed"
    BET_WON = "bet_won"
    BET_LOST = "bet_lost"
    GAME_ROUND_COMPLETE = "game_round_complete"
    PLAYER_SNAPSHOT = "player_snapshot"


class GameType(Enum):
    """Supported game types"""
    SLOTS = "slots"
    ROULETTE = "roulette"
    BLACKJACK = "blackjack"


@dataclass
class BetEvent:
    """
    Immutable event representing a betting action.
    Core of event sourcing - events are facts that happened.
    """
    event_id: str
    player_id: str
    game_type: GameType
    event_type: EventType
    amount: float
    timestamp: int  # milliseconds since epoch
    session_id: str
    bet_id: Optional[str] = None  # Links bet outcome to original bet
    correlation_id: Optional[str] = None  # Distributed tracing across services
    ip_address: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for Kafka serialization"""
        return {
            'event_id': self.event_id,
            'player_id': self.player_id,
            'game_type': self.game_type.value if isinstance(self.game_type, GameType) else self.game_type,
            'event_type': self.event_type.value if isinstance(self.event_type, EventType) else self.event_type,
            'amount': self.amount,
            'timestamp': self.timestamp,
            'session_id': self.session_id,
            'bet_id': self.bet_id,
            'correlation_id': self.correlation_id,
            'ip_address': self.ip_address
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'BetEvent':
        """Create from dictionary (Kafka deserialization)"""
        return cls(
            event_id=data['event_id'],
            player_id=data['player_id'],
            game_type=GameType(data['game_type']),
            event_type=EventType(data['event_type']),
            amount=data['amount'],
            timestamp=data['timestamp'],
            session_id=data['session_id'],
            bet_id=data.get('bet_id'),
            correlation_id=data.get('correlation_id'),
            ip_address=data.get('ip_address')
        )


@dataclass
class PlayerSnapshot:
    """
    Snapshot of player state for efficient reconstruction.
    Space optimization: O(1) instead of O(n) event replay.
    """
    player_id: str
    balance: float
    total_wagered: float
    total_won: float
    total_lost: float
    games_played: int
    win_count: int
    loss_count: int
    last_event_timestamp: int
    snapshot_timestamp: int
    event_count_since_start: int  # Track how many events we're compacting

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'PlayerSnapshot':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class PlayerBalance:
    """
    Denormalized read model for query service.
    Optimized for fast balance lookups - O(1).
    """
    player_id: str
    balance: float
    last_updated: int  # timestamp

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BetCommand:
    """
    Command model for placing bets (command service).
    Represents intention to change state.
    """
    player_id: str
    game_type: str
    amount: float
    session_id: str
    ip_address: Optional[str] = None

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate business rules.
        Returns (is_valid, error_message)
        """
        if self.amount <= 0:
            return False, "Bet amount must be positive"

        if self.amount < 10:
            return False, "Minimum bet is $10"

        if self.amount > 1000:
            return False, "Maximum bet is $1000"

        if self.game_type not in [g.value for g in GameType]:
            return False, f"Invalid game type: {self.game_type}"

        return True, None


# ============================================================================
# API Contract Models (Pydantic)
# Shared request/response DTOs used across multiple services
# ============================================================================

class HealthResponse(BaseModel):
    """Standard health check response - used by all services"""
    status: str
    service: str


class PlaceBetRequest(BaseModel):
    """
    Request model for placing a bet.
    Used by: API Gateway, Command Service
    """
    player_id: str = Field(..., min_length=1, max_length=100, description="Player identifier")
    game_type: str = Field(..., description="Type of game (slots, blackjack, roulette, poker)")
    amount: float = Field(..., gt=0, le=10000, description="Bet amount")
    session_id: str = Field(..., description="Session identifier")
    ip_address: Optional[str] = Field(None, description="Client IP address")


class PlaceBetResponse(BaseModel):
    """
    Response model for placed bet.
    Used by: API Gateway, Command Service
    """
    bet_id: str
    correlation_id: str
    status: str
    message: str
    timestamp: float  # Unix timestamp (seconds since epoch)


class PlayerStats(BaseModel):
    """
    Player statistics response.
    Used by: API Gateway, Query Service
    """
    player_id: str
    balance: float
    games_played: int
    total_wagered: float
    total_won: float
    total_lost: float
    win_count: int
    loss_count: int
    win_rate: float


class LeaderboardEntry(BaseModel):
    """
    Single leaderboard entry.
    Used by: API Gateway, Query Service
    """
    player_id: str
    balance: float
    rank: int


class LeaderboardResponse(BaseModel):
    """
    Leaderboard response wrapper.
    Used by: API Gateway, Query Service
    """
    leaderboard: list[LeaderboardEntry]


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
