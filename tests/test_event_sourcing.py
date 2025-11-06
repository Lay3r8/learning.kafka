"""
Integration tests for Event Sourcing Domain.

Tests event processing, state reconstruction, and snapshots.
"""
import time
from json import loads as json_loads
from redis import Redis
from requests import get, post


class TestEventProcessing:
    """Test event processing and state management."""

    def test_event_correlation(
        self,
        command_service_url: str,
        query_service_url: str
    ):
        """
        Test: Verify events are correlated correctly.

        Each bet should generate:
        1. BET_PLACED event
        2. BET_WON or BET_LOST event (correlated)
        """
        player_id = "correlation_test_player"

        bet_request = {
            "player_id": player_id,
            "game_type": "slots",
            "amount": 100.0,
            "session_id": "correlation_session"
        }

        response = post(
            f"{command_service_url}/api/v1/bets",
            json=bet_request
        )

        assert response.status_code == 202
        bet_data = response.json()

        # Both bet_id and correlation_id should be present
        assert "bet_id" in bet_data
        assert "correlation_id" in bet_data

        # Wait for events to process
        time.sleep(2.0)

        # Verify state was updated (both events processed)
        stats_response = get(
            f"{query_service_url}/api/v1/players/{player_id}/stats"
        )

        assert stats_response.status_code == 200
        stats = stats_response.json()

        # Should have 1 game played (both events processed as one game)
        assert stats["games_played"] == 1
        assert stats["total_wagered"] == 100.0

    def test_state_reconstruction(
        self,
        command_service_url: str,
        query_service_url: str,
        redis_client: Redis,
        clean_redis: None
    ):
        """
        Test: Verify player state is reconstructed correctly from events.

        Tests the core principle of event sourcing: state = f(events)
        """
        player_id = "reconstruction_player"

        # Place multiple bets with known amounts
        bet_amounts = [50.0, 75.0, 100.0]

        for i, amount in enumerate(bet_amounts):
            bet_request = {
                "player_id": player_id,
                "game_type": "blackjack",
                "amount": amount,
                "session_id": f"recon_session_{i}"
            }

            response = post(
                f"{command_service_url}/api/v1/bets",
                json=bet_request
            )
            assert response.status_code == 202

        time.sleep(5.0)

        # Get final state
        stats_response = get(
            f"{query_service_url}/api/v1/players/{player_id}/stats"
        )

        assert stats_response.status_code == 200
        stats = stats_response.json()

        # Verify state reflects all events
        assert stats["games_played"] == 3
        assert stats["total_wagered"] == sum(bet_amounts)  # 225.0

        # Win/loss counts should sum to games played
        assert stats["win_count"] + stats["loss_count"] == 3

    def test_snapshot_creation(
        self,
        command_service_url: str,
        redis_client: Redis,
        clean_redis: None
    ):
        """
        Test: Verify snapshots are created at configured intervals.

        Default SNAPSHOT_INTERVAL is 50 events.
        This test creates enough events to trigger a snapshot.
        """
        player_id = "snapshot_test_player"

        # Place 52 bets to exceed snapshot interval (50)
        for i in range(52):
            bet_request = {
                "player_id": player_id,
                "game_type": "roulette",
                "amount": 10.0,
                "session_id": f"snapshot_session_{i}"
            }

            post(
                f"{command_service_url}/api/v1/bets",
                json=bet_request
            )

        # Wait for processing
        time.sleep(5.0)

        # Check if snapshot exists in Redis
        snapshot_key = f"snapshot:{player_id}:latest"
        snapshot_data = redis_client.get(snapshot_key)

        assert snapshot_data is not None, "Snapshot should be created after 50 events"

        # Verify snapshot content
        snapshot = json_loads(snapshot_data)
        assert snapshot["player_id"] == player_id
        assert "balance" in snapshot
        assert "event_count_since_start" in snapshot
        assert "snapshot_timestamp" in snapshot


class TestReadModelUpdates:
    """Test that read models are updated correctly from events."""

    def test_balance_real_time_update(
        self,
        command_service_url: str,
        query_service_url: str,
        clean_redis: None
    ):
        """
        Test: Verify balance is updated in real-time as events are processed.
        """
        player_id = "realtime_player"

        # Get initial balance (should not exist)
        response = get(
            f"{query_service_url}/api/v1/players/{player_id}/balance"
        )
        assert response.status_code == 404

        # Place a bet
        bet_request = {
            "player_id": player_id,
            "game_type": "slots",
            "amount": 100.0,
            "session_id": "realtime_session"
        }

        post(f"{command_service_url}/api/v1/bets", json=bet_request)

        # Wait for processing
        time.sleep(2.0)

        # Balance should now exist
        response = get(
            f"{query_service_url}/api/v1/players/{player_id}/balance"
        )
        assert response.status_code == 200

        balance_data = response.json()
        assert balance_data["balance"] != 10000.0  # Changed from initial
        assert balance_data["last_updated"] > 0

    def test_leaderboard_auto_update(
        self,
        command_service_url: str,
        query_service_url: str,
        clean_redis: None
    ):
        """
        Test: Verify leaderboard is automatically updated as events occur.
        """
        # Start with empty leaderboard
        response = get(f"{query_service_url}/api/v1/leaderboard")
        assert len(response.json()["leaderboard"]) == 0

        # Add a player
        player_id = "leaderboard_auto_player"
        bet_request = {
            "player_id": player_id,
            "game_type": "blackjack",
            "amount": 50.0,
            "session_id": "lb_auto_session"
        }

        post(f"{command_service_url}/api/v1/bets", json=bet_request)
        time.sleep(2.0)

        # Leaderboard should now have the player
        response = get(f"{query_service_url}/api/v1/leaderboard")
        leaderboard = response.json()["leaderboard"]

        assert len(leaderboard) == 1
        assert leaderboard[0]["player_id"] == player_id
        assert leaderboard[0]["rank"] == 1

    def test_stats_incremental_update(
        self,
        command_service_url: str,
        query_service_url: str,
        clean_redis: None
    ):
        """
        Test: Verify stats are updated incrementally with each event.
        """
        player_id = "incremental_player"

        # Place first bet
        post(
            f"{command_service_url}/api/v1/bets",
            json={
                "player_id": player_id,
                "game_type": "slots",
                "amount": 50.0,
                "session_id": "inc_session_1"
            }
        )
        time.sleep(2.0)

        # Check stats after first bet
        stats1 = get(
            f"{query_service_url}/api/v1/players/{player_id}/stats"
        ).json()

        assert stats1["games_played"] == 1
        assert stats1["total_wagered"] == 50.0

        # Place second bet
        post(
            f"{command_service_url}/api/v1/bets",
            json={
                "player_id": player_id,
                "game_type": "roulette",
                "amount": 75.0,
                "session_id": "inc_session_2"
            }
        )
        time.sleep(2.0)

        # Check stats after second bet
        stats2 = get(
            f"{query_service_url}/api/v1/players/{player_id}/stats"
        ).json()

        # Stats should be incremented
        assert stats2["games_played"] == 2
        assert stats2["total_wagered"] == 125.0  # 50 + 75
        assert stats2["balance"] != stats1["balance"]  # Balance changed
