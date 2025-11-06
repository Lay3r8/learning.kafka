"""
Integration tests for Query Domain.

Tests the read side of CQRS, including player queries,
leaderboards, and statistics endpoints.
"""
import time

from requests import get, post


class TestPlayerQueries:
    """Test player-specific query endpoints."""

    def test_query_nonexistent_player(self, query_service_url: str, clean_redis: None):
        """
        Test: Query balance for player that doesn't exist.

        Should return 404 Not Found.
        """
        response = get(
            f"{query_service_url}/api/v1/players/nonexistent_player/balance"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_query_player_stats_nonexistent(
        self,
        query_service_url: str,
        clean_redis: None
    ):
        """
        Test: Query stats for player that doesn't exist.
        """
        response = get(
            f"{query_service_url}/api/v1/players/ghost_player/stats"
        )

        assert response.status_code == 404

    def test_player_stats_accuracy(
        self,
        command_service_url: str,
        query_service_url: str,
        clean_redis: None
    ):
        """
        Test: Verify player statistics are calculated correctly.

        Places known bets and verifies stats match expectations.
        """
        player_id = "test_stats_player"

        # Place 10 small bets to get statistical sample
        for i in range(10):
            bet_request = {
                "player_id": player_id,
                "game_type": "slots",
                "amount": 10.0,
                "session_id": f"stats_session_{i}"
            }

            response = post(
                f"{command_service_url}/api/v1/bets",
                json=bet_request
            )
            assert response.status_code == 202

        time.sleep(5.0)

        # Get stats
        stats_response = get(
            f"{query_service_url}/api/v1/players/{player_id}/stats"
        )

        assert stats_response.status_code == 200
        stats = stats_response.json()

        # Verify statistics
        assert stats["games_played"] == 10
        assert stats["total_wagered"] == 100.0
        assert stats["win_count"] + stats["loss_count"] == 10

        # Win rate should be reasonable (0-100%)
        assert 0 <= stats["win_rate"] <= 100

        # Total won + total lost should relate to balance change
        initial_balance = 10000.0
        balance_change = stats["balance"] - initial_balance
        expected_change = stats["total_won"] - stats["total_wagered"]

        # Allow small floating point differences
        assert abs(balance_change - expected_change) < 0.01


class TestLeaderboard:
    """Test leaderboard functionality."""

    def test_leaderboard_default_limit(
        self,
        command_service_url: str,
        query_service_url: str,
        clean_redis: None
    ):
        """
        Test: Get leaderboard with default limit (10 players).
        """
        # Create 5 players with different balances
        for i in range(5):
            player_id = f"leaderboard_player_{i:03d}"

            # Each player makes different number of bets
            for _ in range(i + 1):
                bet_request = {
                    "player_id": player_id,
                    "game_type": "roulette",
                    "amount": 50.0,
                    "session_id": f"lb_session_{i}"
                }

                post(
                    f"{command_service_url}/api/v1/bets",
                    json=bet_request
                )

        time.sleep(3.0)

        # Get leaderboard
        response = get(f"{query_service_url}/api/v1/leaderboard")

        assert response.status_code == 200
        data = response.json()

        assert "leaderboard" in data
        leaderboard = data["leaderboard"]

        # Should have entries for all players
        assert len(leaderboard) == 5

        # Verify structure
        for entry in leaderboard:
            assert "player_id" in entry
            assert "balance" in entry
            assert "rank" in entry

        # Verify ranking is correct (descending by balance)
        for i in range(len(leaderboard) - 1):
            assert leaderboard[i]["balance"] >= leaderboard[i + 1]["balance"]

        # Verify ranks are sequential
        for i, entry in enumerate(leaderboard, start=1):
            assert entry["rank"] == i

    def test_leaderboard_custom_limit(
        self,
        command_service_url: str,
        query_service_url: str,
        clean_redis: None
    ):
        """
        Test: Get leaderboard with custom limit.
        """
        # Create 10 players
        for i in range(10):
            player_id = f"top_player_{i:03d}"
            bet_request = {
                "player_id": player_id,
                "game_type": "blackjack",
                "amount": 20.0,
                "session_id": f"top_session_{i}"
            }
            post(f"{command_service_url}/api/v1/bets", json=bet_request)

        time.sleep(3.0)

        # Get top 3
        response = get(f"{query_service_url}/api/v1/leaderboard?limit=3")

        assert response.status_code == 200
        leaderboard = response.json()["leaderboard"]

        assert len(leaderboard) == 3

    def test_leaderboard_limit_validation(self, query_service_url: str):
        """
        Test: Leaderboard limit parameter validation.

        Should enforce 1-100 range.
        """
        # Test limit too low
        response = get(f"{query_service_url}/api/v1/leaderboard?limit=0")
        assert response.status_code == 422

        # Test limit too high
        response = get(f"{query_service_url}/api/v1/leaderboard?limit=101")
        assert response.status_code == 422

        # Test valid limits
        response = get(f"{query_service_url}/api/v1/leaderboard?limit=1")
        assert response.status_code == 200

        response = get(f"{query_service_url}/api/v1/leaderboard?limit=100")
        assert response.status_code == 200

    def test_empty_leaderboard(self, query_service_url: str, clean_redis: None):
        """
        Test: Get leaderboard when no players exist.
        """
        response = get(f"{query_service_url}/api/v1/leaderboard")

        assert response.status_code == 200
        data = response.json()
        assert data["leaderboard"] == []


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_command_service_health(self, command_service_url: str):
        """Test command service health endpoint."""
        response = get(f"{command_service_url}/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "command-service"

    def test_query_service_health(self, query_service_url: str):
        """Test query service health endpoint."""
        response = get(f"{query_service_url}/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "query-service"
        assert data["redis"] == "connected"
