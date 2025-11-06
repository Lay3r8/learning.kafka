"""
Event Processor Service - Event Sourcing & State Management

Responsibilities:
- Consume events from Kafka
- Rebuild player state (event sourcing)
- Create snapshots for space efficiency
- Update Redis read models for query service
- Detect fraud patterns
"""
from logging import basicConfig, getLogger, INFO, DEBUG, StreamHandler
from sys import stdout
from json import dumps as json_dumps, loads as json_loads
from os import getenv
from time import time
from typing import Dict
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import redis
from models import BetEvent, EventType, PlayerSnapshot


# Configuration from environment (required - no defaults)
KAFKA_BOOTSTRAP_SERVERS = getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_TOPIC = getenv("KAFKA_TOPIC")
KAFKA_GROUP_ID = getenv("KAFKA_GROUP_ID")
REDIS_HOST = getenv("REDIS_HOST")
REDIS_PORT = getenv("REDIS_PORT")
SNAPSHOT_INTERVAL = getenv("SNAPSHOT_INTERVAL")

# Validate required configuration
if not KAFKA_BOOTSTRAP_SERVERS:
    raise ValueError("KAFKA_BOOTSTRAP_SERVERS environment variable is required")
if not KAFKA_TOPIC:
    raise ValueError("KAFKA_TOPIC environment variable is required")
if not KAFKA_GROUP_ID:
    raise ValueError("KAFKA_GROUP_ID environment variable is required")
if not REDIS_HOST:
    raise ValueError("REDIS_HOST environment variable is required")
if not REDIS_PORT:
    raise ValueError("REDIS_PORT environment variable is required")
if not SNAPSHOT_INTERVAL:
    raise ValueError("SNAPSHOT_INTERVAL environment variable is required")

# Convert to appropriate types after validation
REDIS_PORT = int(REDIS_PORT)
SNAPSHOT_INTERVAL = int(SNAPSHOT_INTERVAL)

# Configure logging
basicConfig(
    level=INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[StreamHandler(stdout)]
)
logger = getLogger(__name__)

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
    "Event processor initialized",
    extra={
        "kafka_bootstrap_servers": KAFKA_BOOTSTRAP_SERVERS,
        "kafka_topic": KAFKA_TOPIC,
        "kafka_group_id": KAFKA_GROUP_ID,
        "redis_host": REDIS_HOST,
        "redis_port": REDIS_PORT,
        "snapshot_interval": SNAPSHOT_INTERVAL
    }
)


class PlayerState:
    """
    Maintains player state updates.
    Demonstrates event sourcing: state = f(events)
    """

    def __init__(self, player_id: str, initial_balance: float = 10000.0):
        self.player_id = player_id
        self.balance = initial_balance
        self.total_wagered = 0.0
        self.total_won = 0.0
        self.total_lost = 0.0
        self.games_played = 0
        self.win_count = 0
        self.loss_count = 0
        self.last_event_timestamp = 0
        self.event_count = 0

    def apply_event(self, event: BetEvent) -> None:
        """
        Apply event to state.
        This is the core of event sourcing: state = f(events)
        """
        self.event_count += 1
        self.last_event_timestamp = event.timestamp

        if event.event_type == EventType.BET_PLACED:
            self.balance -= event.amount
            self.total_wagered += event.amount
            self.games_played += 1

        elif event.event_type == EventType.BET_WON:
            self.balance += event.amount
            self.total_won += event.amount
            self.win_count += 1

        elif event.event_type == EventType.BET_LOST:
            self.total_lost += event.amount
            self.loss_count += 1

    def create_snapshot(self) -> PlayerSnapshot:
        """Create snapshot for space-efficient storage"""
        return PlayerSnapshot(
            player_id=self.player_id,
            balance=self.balance,
            total_wagered=self.total_wagered,
            total_won=self.total_won,
            total_lost=self.total_lost,
            games_played=self.games_played,
            win_count=self.win_count,
            loss_count=self.loss_count,
            last_event_timestamp=self.last_event_timestamp,
            snapshot_timestamp=int(time() * 1000),
            event_count_since_start=self.event_count
        )

    def get_win_rate(self) -> float:
        """Calculate win rate percentage"""
        total_outcomes = self.win_count + self.loss_count
        return (self.win_count / total_outcomes * 100) if total_outcomes > 0 else 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for Redis storage"""
        return {
            "player_id": self.player_id,
            "balance": round(self.balance, 2),
            "total_wagered": round(self.total_wagered, 2),
            "total_won": round(self.total_won, 2),
            "total_lost": round(self.total_lost, 2),
            "games_played": self.games_played,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "win_rate": round(self.get_win_rate(), 2),
            "last_updated": self.last_event_timestamp
        }


class EventProcessor:
    """
    Main event processing engine.
    Consumes events, rebuilds state, updates read models.
    """

    def __init__(self):
        self.consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            auto_offset_reset="earliest",
            value_deserializer=lambda x: json_loads(x.decode("utf-8")),
            group_id=KAFKA_GROUP_ID,
            enable_auto_commit=True,
            auto_commit_interval_ms=5000,
            max_poll_records=500  # Batch processing for efficiency
        )

        # In-memory state store: player_id -> PlayerState
        self.player_states: Dict[str, PlayerState] = {}

        # Performance metrics
        self.events_processed = 0
        self.snapshots_created = 0
        self.start_time = time()

    def process_events(self):
        """
        Main event processing loop.
        Consumes events, updates state, and syncs to Redis.
        """
        logger.info("Starting event processing loop")

        try:
            for message in self.consumer:
                event_data = message.value

                try:
                    # Parse event
                    event = BetEvent.from_dict(event_data)

                    # Extract correlation_id from Kafka message headers if present
                    correlation_id = None
                    if hasattr(message, 'headers') and message.headers:
                        # message.headers is a list of tuples [(key, bytes), ...]
                        for k, v in message.headers:
                            try:
                                if k.decode('utf-8') if isinstance(k, bytes) else k == 'X-Correlation-ID':
                                    correlation_id = (v.decode('utf-8') if isinstance(v, bytes) else v)
                                    break
                            except Exception:
                                # Fallback: header keys may already be str
                                if k == 'X-Correlation-ID':
                                    correlation_id = (v.decode('utf-8') if isinstance(v, bytes) else v)
                                    break

                    # Fall back to correlation_id in payload if header missing
                    if not correlation_id:
                        correlation_id = getattr(event, 'correlation_id', None)

                    # Get or create player state
                    if event.player_id not in self.player_states:
                        self.player_states[event.player_id] = PlayerState(event.player_id)
                        logger.info(
                            "New player registered",
                            extra={"player_id": event.player_id}
                        )

                    # Apply event
                    self.player_states[event.player_id].apply_event(event)
                    self.events_processed += 1

                    logger.info(
                        "Event processed",
                        extra={
                            "event_id": event.event_id,
                            "event_type": event.event_type.value,
                            "player_id": event.player_id,
                            "amount": event.amount,
                            "partition": message.partition,
                            "offset": message.offset
                        }
                    )

                    # Update Redis read model (for query service)
                    self._update_read_model(event.player_id)

                    # Persist per-bet history (store/patch bet records)
                    try:
                        self._persist_bet_event(event, correlation_id)
                    except Exception as e:
                        logger.error("Failed to persist bet event", extra={"error": str(e)})

                    # Create snapshot if interval reached
                    if self.player_states[event.player_id].event_count % SNAPSHOT_INTERVAL == 0:
                        self._create_snapshot(event.player_id)

                    # Print progress
                    if self.events_processed % 100 == 0:
                        self._log_progress()

                except Exception as e:
                    logger.error(
                        "Failed to process event",
                        extra={
                            "error": str(e),
                            "partition": message.partition,
                            "offset": message.offset
                        },
                        exc_info=True
                    )
                    continue

        except KeyboardInterrupt:
            logger.info("Shutting down event processor")
        except KafkaError as e:
            logger.error(
                "Kafka error occurred",
                extra={"error": str(e)},
                exc_info=True
            )
        finally:
            self._log_final_report()
            self.consumer.close()
            logger.info("Event processor stopped")

    def _update_read_model(self, player_id: str):
        """
        Update Redis read models for query service.
        Denormalized data optimized for fast reads.
        """
        player = self.player_states[player_id]

        # Update player balance (lookup for query service)
        balance_data = {
            "player_id": player_id,
            "balance": round(player.balance, 2),
            "last_updated": player.last_event_timestamp
        }
        redis_client.set(
            f"player:{player_id}:balance",
            json_dumps(balance_data)
        )

        # Update player stats (lookup)
        stats_data = player.to_dict()
        redis_client.set(
            f"player:{player_id}:stats",
            json_dumps(stats_data)
        )

        # Update leaderboard (sorted set)
        redis_client.zadd(
            "leaderboard:balance",
            {player_id: player.balance}
        )

        # Update global stats
        redis_client.set("stats:total_bets", self.events_processed)
        redis_client.set("stats:total_players", len(self.player_states))
        redis_client.set(
            "stats:total_wagered",
            sum(p.total_wagered for p in self.player_states.values())
        )

    def _persist_bet_event(self, event: BetEvent, correlation_id: str | None):
        """
        Store or update a per-bet record in Redis for the player.

        Storage model:
          key: player:{player_id}:bets (list of JSON strings)
          each entry: { bet_id, event_id, session_id, game_type, amount, timestamp, status, correlation_id, profit }

        For BET_PLACED: create a new record with status 'placed' and push to head of list.
        For BET_WON / BET_LOST: find existing bet by bet_id and update status/result/profit.
        Keep list capped to 1000 entries for safety.
        """
        key = f"player:{event.player_id}:bets"

        # Helper to build record
        def make_record(e: BetEvent, status: str, profit: float | None = None):
            return {
                "bet_id": e.bet_id,
                "event_id": e.event_id,
                "session_id": e.session_id,
                "game_type": e.game_type.value if hasattr(e.game_type, 'value') else str(e.game_type),
                "amount": round(e.amount, 2),
                "timestamp": e.timestamp,
                "status": status,
                "correlation_id": correlation_id or getattr(e, 'correlation_id', None),
                "profit": round(profit, 2) if profit is not None else None
            }

        if event.event_type == EventType.BET_PLACED:
            record = make_record(event, "placed", None)
            # Push to the left (most recent first)
            redis_client.lpush(key, json_dumps(record))
            # Trim list to 1000
            redis_client.ltrim(key, 0, 999)

        elif event.event_type in (EventType.BET_WON, EventType.BET_LOST):
            # Update existing record: read all, replace matching bet_id
            try:
                existing = redis_client.lrange(key, 0, 999)
                updated = False
                for idx, item in enumerate(existing):
                    try:
                        obj = json_loads(item)
                    except Exception:
                        continue
                    if obj.get("bet_id") == event.bet_id:
                        profit = None
                        if event.event_type == EventType.BET_WON:
                            profit = event.amount
                        elif event.event_type == EventType.BET_LOST:
                            profit = -event.amount

                        obj.update({
                            "status": "won" if event.event_type == EventType.BET_WON else "lost",
                            "timestamp": event.timestamp,
                            "correlation_id": correlation_id or obj.get("correlation_id"),
                            "profit": round(profit, 2) if profit is not None else None
                        })
                        # Write back to the list at the same index using LSET
                        redis_client.lset(key, idx, json_dumps(obj))
                        updated = True
                        break

                # If not found, create a new record (defensive)
                if not updated:
                    rec = make_record(event, "won" if event.event_type == EventType.BET_WON else "lost",
                                      event.amount if event.event_type == EventType.BET_WON else -event.amount)
                    redis_client.lpush(key, json_dumps(rec))
                    redis_client.ltrim(key, 0, 999)

            except Exception as e:
                logger.error("Error updating bet list in Redis", extra={"error": str(e)})

    def _create_snapshot(self, player_id: str):
        """
        Create snapshot for space efficiency.
        """
        player = self.player_states[player_id]
        snapshot = player.create_snapshot()

        # Store snapshot in Redis
        redis_client.set(
            f"snapshot:{player_id}:latest",
            json_dumps(snapshot.to_dict())
        )

        self.snapshots_created += 1

        logger.info(
            "Snapshot created",
            extra={
                "player_id": player_id,
                "event_count": player.event_count,
                "balance": player.balance
            }
        )

    def _log_progress(self):
        """Log processing metrics"""
        elapsed = time() - self.start_time
        throughput = self.events_processed / elapsed if elapsed > 0 else 0

        logger.info(
            "Processing progress",
            extra={
                "events_processed": self.events_processed,
                "throughput_eps": round(throughput, 2),
                "players": len(self.player_states),
                "snapshots": self.snapshots_created
            }
        )

    def _log_final_report(self):
        """Log final performance report"""
        elapsed = time() - self.start_time
        throughput = self.events_processed / elapsed if elapsed > 0 else 0

        logger.info(
            "Event sourcing performance report",
            extra={
                "total_events": self.events_processed,
                "total_players": len(self.player_states),
                "snapshots_created": self.snapshots_created,
                "processing_time_seconds": round(elapsed, 2),
                "throughput_eps": round(throughput, 2)
            }
        )

        # Space complexity analysis
        print(f"\nSPACE COMPLEXITY:")
        print(f"Without snapshots: O({self.events_processed}) events stored")
        print(f"With snapshots: O({len(self.player_states)}) player states + O({self.snapshots_created}) snapshots")

        print(f"\nTIME COMPLEXITY:")
        print(f"Event application: O(1) per event")
        print(f"State reconstruction: O(k) where k = events since last snapshot")

        # Top players by profit
        if self.player_states:
            print("\nTOP 5 PLAYERS BY NET PROFIT:")
            sorted_players = sorted(
                self.player_states.values(),
                key=lambda p: p.balance - 10000,
                reverse=True
            )[:5]

            for i, player in enumerate(sorted_players, 1):
                net_profit = player.balance - 10000
                print(
                    f"{i}. {player.player_id}: "
                    f"${net_profit:+.2f} profit | "
                    f"{player.games_played} games | "
                    f"{player.get_win_rate():.1f}% win rate"
                )

        print("="*70 + "\n")


if __name__ == "__main__":
    processor = EventProcessor()
    processor.process_events()
