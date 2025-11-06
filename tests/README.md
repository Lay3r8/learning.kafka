# Integration Tests

Comprehensive integration tests for the Gaming Event System.

## Overview

These tests verify the complete CQRS event-driven architecture by:
1. Starting all services via Docker Compose
2. Testing end-to-end workflows
3. Verifying event processing and state consistency
4. Testing edge cases and error handling

## Test Organization

Tests are organized by domain:

### `test_betting_domain.py`
Tests for betting operations and validation:
- Bet placement and balance updates
- Multiple bets for same player
- Concurrent bet handling
- Validation rules (min/max amounts, game types)
- Edge cases (large amounts, concurrent operations)

### `test_query_domain.py`
Tests for query operations:
- Player balance queries
- Player statistics queries
- Leaderboard functionality
- Query parameter validation
- Non-existent player handling
- Health check endpoints

### `test_event_sourcing.py`
Tests for event sourcing mechanics:
- Event correlation (bet_id, correlation_id)
- State reconstruction from events
- Snapshot creation and storage
- Real-time read model updates
- Incremental state updates
- Leaderboard auto-updates

## Running Tests

### Prerequisites

1. Install test dependencies:
```bash
pip install -r tests/requirements.txt
```

2. Ensure Docker and Docker Compose are installed and running.

### Run All Tests

```bash
# From project root
pytest tests/ -v
```

### Run Specific Test File

```bash
# Betting domain tests only
pytest tests/test_betting_domain.py -v

# Query domain tests only
pytest tests/test_query_domain.py -v

# Event sourcing tests only
pytest tests/test_event_sourcing.py -v
```

### Run Specific Test

```bash
pytest tests/test_betting_domain.py::TestBettingFlow::test_place_bet_and_retrieve_balance -v
```

### Run with Coverage

```bash
pytest tests/ --cov=services --cov-report=html
```

## Test Fixtures

### Session-scoped Fixtures
- `docker_services`: Starts and stops Docker Compose services for entire test session

### Function-scoped Fixtures
- `redis_client`: Provides Redis client for assertions
- `clean_redis`: Cleans Redis before and after each test
- `command_service_url`: URL for command service (http://localhost:5000)
- `query_service_url`: URL for query service (http://localhost:5001)

## Test Patterns

### Testing CQRS Flow

```python
def test_cqrs_flow(command_service_url, query_service_url, clean_redis):
    # 1. Send command
    response = requests.post(f"{command_service_url}/api/v1/bets", json=bet_data)

    # 2. Wait for event processing
    wait_for_event_processing(2.0)

    # 3. Query result
    result = requests.get(f"{query_service_url}/api/v1/players/{player_id}/balance")

    # 4. Assert expectations
    assert result.status_code == 200
```

### Testing Event Sourcing

```python
def test_event_sourcing(redis_client):
    # Verify snapshot creation
    snapshot_key = f"snapshot:{player_id}:latest"
    snapshot_data = redis_client.get(snapshot_key)
    assert snapshot_data is not None
```

## Performance Considerations

- Tests use `wait_for_event_processing()` to allow async event processing
- Default wait is 1-3 seconds depending on test complexity
- Concurrent tests use ThreadPoolExecutor for parallel requests
- Session-scoped fixtures minimize Docker Compose start/stop overhead

## Debugging Failed Tests

### View service logs:
```bash
docker compose logs command-service
docker compose logs query-service
docker compose logs event-processor
docker compose logs kafka
```

### Check Redis state:
```bash
docker exec -it redis redis-cli
> KEYS *
> GET player:player_id:balance
```

### Run tests with output:
```bash
pytest tests/ -v -s  # -s shows print statements
```

## CI/CD Integration

These tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run Integration Tests
  run: |
    pip install -r tests/requirements.txt
    pytest tests/ -v --junitxml=test-results.xml
```

## Test Coverage

Current test coverage includes:
- ✅ Happy path scenarios
- ✅ Validation and error handling
- ✅ Concurrent operations
- ✅ Edge cases (min/max values)
- ✅ State consistency
- ✅ Event correlation
- ✅ Snapshot creation
- ✅ Real-time updates

## Known Limitations

- Tests require ~30 seconds for service startup
- Snapshot tests need 50+ events (may be slow)
- Concurrent tests may have timing variations
- Tests require ports 5000, 5001, 6379, 9092 to be available

## Future Enhancements

- [ ] Performance/load tests
- [ ] Chaos engineering tests (service failures)
- [ ] Multi-session betting scenarios
- [ ] Fraud detection tests
- [ ] Data consistency tests under high load
