"""
Pytest configuration and shared fixtures for integration tests.
"""
import subprocess
import time
from typing import Generator

import pytest
import requests
from redis import Redis


@pytest.fixture(scope="session")
def docker_services() -> Generator[None, None, None]:
    """
    Fixture to manage Docker Compose services for the entire test session.
    Starts services before tests and stops them after.
    """
    # Start services
    print("\nStarting Docker Compose services...")
    subprocess.run(
        ["docker", "compose", "up", "-d", "--build"],
        check=True,
        cwd="/home/simon/workspace/learning/kafka"
    )

    # Wait for services to be healthy
    print("Waiting for services to be healthy...")
    max_retries = 30
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Check command service health
            cmd_response = requests.get("http://localhost:5000/health", timeout=2)
            # Check query service health
            query_response = requests.get("http://localhost:5001/health", timeout=2)

            if cmd_response.status_code == 200 and query_response.status_code == 200:
                print("All services are healthy!")
                break
        except requests.RequestException:
            pass

        retry_count += 1
        time.sleep(2)

    if retry_count >= max_retries:
        raise RuntimeError("Services failed to become healthy within timeout")

    # Additional wait for event processor to be ready
    time.sleep(3)

    yield

    # Teardown: stop services
    print("\nStopping Docker Compose services...")
    subprocess.run(
        ["docker", "compose", "down"],
        check=False,
        cwd="/home/simon/workspace/learning/kafka"
    )


@pytest.fixture(scope="function")
def redis_client(docker_services) -> Redis:
    """
    Fixture providing a Redis client for test assertions.
    """
    client = Redis(
        host='localhost',
        port=6379,
        decode_responses=True
    )
    return client


@pytest.fixture(scope="function")
def clean_redis(redis_client: Redis) -> Generator[None, None, None]:
    """
    Fixture to clean Redis before and after each test.
    """
    # Clean before test
    redis_client.flushdb()
    yield
    # Clean after test
    redis_client.flushdb()


@pytest.fixture(scope="function")
def command_service_url(docker_services) -> str:
    """URL for the command service API."""
    return "http://localhost:5000"


@pytest.fixture(scope="function")
def query_service_url(docker_services) -> str:
    """URL for the query service API."""
    return "http://localhost:5001"
