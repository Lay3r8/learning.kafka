"""
Integration tests for Betting Domain.

Tests the complete flow of placing bets, processing events,
and querying results through the CQRS architecture.
"""
import time

from requests import get, post
from redis import Redis


class TestBettingFlow:
    """Test the complete betting workflow from command to query."""

    def test_place_bet_and_retrieve_balance(
        self,
        command_service_url: str,
        query_service_url: str,
        clean_redis: None
    ):
        """
        Test: Place a bet and verify player balance is updated.

        Flow:
        1. Place bet via command service
        2. Wait for event processing
        3. Query player balance via query service
        4. Verify balance is correct
        """
        player_id = "test_player_001"
        bet_amount = 100.0

        # Step 1: Place bet
        bet_request = {
            "player_id": player_id,
            "game_type": "slots",
            "amount": bet_amount,
            "session_id": "test_session_001"
        }

        response = post(
            f"{command_service_url}/api/v1/bets",
            json=bet_request
        )

        assert response.status_code == 202
        bet_response = response.json()
        assert "bet_id" in bet_response
        assert "correlation_id" in bet_response
        assert bet_response["status"] == "accepted"

        # Step 2: Wait for event processing
        time.sleep(5.0)

        # Step 3: Query balance
        balance_response = get(
            f"{query_service_url}/api/v1/players/{player_id}/balance"
        )

        assert balance_response.status_code == 200
        balance_data = balance_response.json()

        # Step 4: Verify balance
        assert balance_data["player_id"] == player_id
        # Initial balance is 10000, bet deducts amount
        # Game outcome adds or keeps deduction
        assert balance_data["balance"] != 10000.0  # Balance changed
        assert "last_updated" in balance_data

    def test_multiple_bets_same_player(
        self,
        command_service_url: str,
        query_service_url: str,
        redis_client: Redis,
        clean_redis: None
    ):
        """
        Test: Place multiple bets for the same player.

        Verifies that:
        - Multiple events are processed correctly
        - Player state is updated incrementally
        - Statistics are accumulated properly
        """
        player_id = "test_player_multi"

        # Place 3 bets
        bet_ids = []
        for i in range(3):
            bet_request = {
                "player_id": player_id,
                "game_type": "slots",
                "amount": 50.0,
                "session_id": f"session_{i}"
            }

            response = post(
                f"{command_service_url}/api/v1/bets",
                json=bet_request
            )

            assert response.status_code == 202
            bet_ids.append(response.json()["bet_id"])

        # Wait for all events to process
        time.sleep(3.0)

        # Check player stats
        stats_response = get(
            f"{query_service_url}/api/v1/players/{player_id}/stats"
        )

        assert stats_response.status_code == 200
        stats = stats_response.json()

        # Verify stats accumulation
        assert stats["player_id"] == player_id
        assert stats["games_played"] == 3
        assert stats["total_wagered"] == 150.0  # 3 bets * 50
        assert stats["balance"] != 10000.0  # Changed from initial
        assert 0 <= stats["win_rate"] <= 100  # Valid percentage

    def test_invalid_bet_amount(self, command_service_url: str):
        """
        Test: Attempt to place bet with invalid amount.

        Verifies validation rules:
        - Minimum bet is $10
        - Maximum bet is $1000
        """
        player_id = "test_player_validation"

        # Test below minimum
        bet_request = {
            "player_id": player_id,
            "game_type": "slots",
            "amount": 5.0,  # Below $10 minimum
            "session_id": "validation_test"
        }

        response = post(
            f"{command_service_url}/api/v1/bets",
            json=bet_request
        )

        assert response.status_code == 422  # Validation error

        # Test above maximum
        bet_request["amount"] = 1500.0  # Above $1000 maximum

        response = post(
            f"{command_service_url}/api/v1/bets",
            json=bet_request
        )

        assert response.status_code == 422  # Validation error

    def test_invalid_game_type(self, command_service_url: str):
        """
        Test: Attempt to place bet with invalid game type.
        """
        bet_request = {
            "player_id": "test_player_game",
            "game_type": "invalid_game",  # Not in GameType enum
            "amount": 100.0,
            "session_id": "game_validation"
        }

        response = post(
            f"{command_service_url}/api/v1/bets",
            json=bet_request
        )

        assert response.status_code == 422  # Validation error


class TestBettingEdgeCases:
    """Test edge cases and error handling in betting domain."""

    def test_concurrent_bets_same_player(
        self,
        command_service_url: str,
        query_service_url: str,
        clean_redis: None
    ):
        """
        Test: Place concurrent bets for the same player.

        Verifies that event sourcing handles concurrent updates correctly.
        """
        player_id = "test_player_concurrent"

        # Send multiple bets concurrently (not waiting between them)
        import concurrent.futures

        def place_bet(bet_num: int):
            bet_request = {
                "player_id": player_id,
                "game_type": "roulette",
                "amount": 25.0,
                "session_id": f"concurrent_session_{bet_num}"
            }
            return post(
                f"{command_service_url}/api/v1/bets",
                json=bet_request
            )

        # Place 5 concurrent bets
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(place_bet, i) for i in range(5)]
            responses = [f.result() for f in futures]

        # All should succeed
        assert all(r.status_code == 202 for r in responses)

        # Wait for processing
        time.sleep(3.0)

        # Verify final state is consistent
        stats_response = get(
            f"{query_service_url}/api/v1/players/{player_id}/stats"
        )

        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats["games_played"] == 5
        assert stats["total_wagered"] == 125.0  # 5 * 25

    def test_large_bet_amount(
        self,
        command_service_url: str,
        query_service_url: str,
        clean_redis: None
    ):
        """
        Test: Place maximum allowed bet amount.
        """
        player_id = "test_player_whale"

        bet_request = {
            "player_id": player_id,
            "game_type": "blackjack",
            "amount": 1000.0,  # Maximum allowed
            "session_id": "whale_session"
        }

        response = post(
            f"{command_service_url}/api/v1/bets",
            json=bet_request
        )

        assert response.status_code == 202

        time.sleep(2.0)

        # Verify balance updated correctly for large amount
        balance_response = get(
            f"{query_service_url}/api/v1/players/{player_id}/balance"
        )

        assert balance_response.status_code == 200
        assert balance_response.json()["balance"] != 10000.0
