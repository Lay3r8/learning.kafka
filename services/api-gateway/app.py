"""
API Gateway - Experience API Layer (BFF Pattern)

Responsibilities:
- Single entry point for external clients (frontend)
- CORS handling
- JWT token verification (Auth0)
- Request routing to internal services
- Response aggregation
- Rate limiting and security
- API versioning
"""
from logging import basicConfig, getLogger, INFO, StreamHandler
from typing import AsyncIterator, TypedDict
from sys import stdout
from os import getenv
from fastapi import FastAPI, HTTPException, status, Request, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient, Limits, TimeoutException, RequestError
from contextlib import asynccontextmanager
from uvicorn import run as uvicorn_run
from lib.auth import verify_jwt_token, check_player_matches_claims, has_role
from uuid import uuid4
from models import (
    PlaceBetRequest,
    PlaceBetResponse as BetResponse,
    PlayerStats,
    LeaderboardResponse,
    HealthResponse as BaseHealthResponse,
)


COMMAND_SERVICE_URL = getenv("COMMAND_SERVICE_URL")
QUERY_SERVICE_URL = getenv("QUERY_SERVICE_URL")
USER_SERVICE_URL = getenv("USER_SERVICE_URL")
if not COMMAND_SERVICE_URL:
    raise ValueError("COMMAND_SERVICE_URL environment variable is required")
if not QUERY_SERVICE_URL:
    raise ValueError("QUERY_SERVICE_URL environment variable is required")
if not USER_SERVICE_URL:
    raise ValueError("USER_SERVICE_URL environment variable is required")

basicConfig(
    level=INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[StreamHandler(stdout)]
)
logger = getLogger(__name__)


# Gateway-specific HealthResponse model
class HealthResponse(BaseHealthResponse):
    """Extended health response for API Gateway - includes backend service status"""
    gateway_version: str = "1.0.0"
    backend_services: dict


class State(TypedDict):
    http_client: AsyncClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[State]:
    """Application lifespan context - initialize and cleanup shared resources.

    Uses `app.state` to avoid module-level globals.
    """
    logger.info("API Gateway starting up")
    logger.info(f"Command Service URL: {COMMAND_SERVICE_URL}")
    logger.info(f"Query Service URL: {QUERY_SERVICE_URL}")
    logger.info(f"User Service URL: {USER_SERVICE_URL}")
    logger.info("HTTP client initialized")
    try:
        async with AsyncClient(
            timeout=10.0,
            limits=Limits(max_keepalive_connections=20, max_connections=100),
        ) as client:
            yield {"http_client": client}
    finally:
        if app.state.http_client is not None:
            await app.state.http_client.aclose()
            logger.info("HTTP client closed")
            logger.info("API Gateway shutdown")


app = FastAPI(
    title="Gaming API Gateway",
    description="Experience API Layer - Single entry point for frontend applications",
    version="1.0.0",
    lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # Frontend production (Docker)
        "http://localhost:5173",      # Frontend dev (Vite)
        "http://localhost:5174",      # Frontend dev alternative port
        "http://frontend:3000",       # Docker internal
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health Check Endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """
    Gateway health check - also checks backend services
    """
    backend_status = {}

    # Check Command Service
    try:
        response = await request.state.http_client.get(f"{COMMAND_SERVICE_URL}/health", timeout=2.0)
        backend_status["command_service"] = "healthy" if response.status_code == 200 else "degraded"
    except Exception as e:
        backend_status["command_service"] = "down"
        logger.error(f"Command service health check failed: {e}")

    # Check Query Service
    try:
        response = await request.state.http_client.get(f"{QUERY_SERVICE_URL}/health", timeout=2.0)
        backend_status["query_service"] = "healthy" if response.status_code == 200 else "degraded"
    except Exception as e:
        backend_status["query_service"] = "down"
        logger.error(f"Query service health check failed: {e}")

    overall_status = "healthy" if all(s == "healthy" for s in backend_status.values()) else "degraded"

    return HealthResponse(
        status=overall_status,
        service="api-gateway",
        backend_services=backend_status
    )


# Command Operations (Write Side)
@app.post("/api/v1/bets", response_model=BetResponse, status_code=status.HTTP_201_CREATED)
async def place_bet(
    request: PlaceBetRequest,
    req: Request,
    claims: dict = Depends(verify_jwt_token)
):
    """
    Place a new bet - Routes to Command Service (PROTECTED)

    This endpoint:
    1. Verifies JWT token
    2. Validates the request
    3. Ensures player_id matches authenticated user
    4. Adds client metadata (IP address)
    5. Forwards to Command Service
    6. Returns the response

    Requires: Valid JWT token in Authorization header
    """
    try:
        logger.info(
            f"Place bet - Auth check for requested player '{request.player_id}'"
        )

        check_player_matches_claims(request.player_id, claims, action="place_bet")

        # Add IP address if not provided
        if not request.ip_address:
            request.ip_address = req.client.host if req.client else "unknown"

        # Correlation ID handling: accept incoming or generate new
        correlation_id = req.headers.get("X-Correlation-ID") or str(uuid4())

        # Forward to Command Service, propagating correlation header and auth
        forward_headers = {"X-Correlation-ID": correlation_id}
        auth_header = req.headers.get("authorization") or req.headers.get("Authorization")
        if auth_header:
            forward_headers["Authorization"] = auth_header

        response = await req.state.http_client.post(
            f"{COMMAND_SERVICE_URL}/api/v1/bets",
            json=request.model_dump(),
            headers=forward_headers,
            timeout=5.0,
        )

        if response.status_code == 202:  # Fixed: 202 Accepted, not 201 Created
            logger.info(
                "Bet placed successfully",
                extra={
                    "player_id": request.player_id,
                    "authenticated_user": claims.get("sub"),
                    "amount": request.amount,
                    "game_type": request.game_type
                }
            )
            # Ensure we return the correlation id used for end-to-end tracing
            # Attach it to the gateway response headers so clients see it too
            return Response(content=response.content, status_code=202, media_type="application/json", headers={"X-Correlation-ID": correlation_id})
        else:
            error_detail = response.json().get("detail", "Failed to place bet")
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

    except TimeoutException:
        logger.error("Command service timeout")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Command service is not responding"
        )
    except RequestError as e:
        logger.error(f"Command service connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Command service is unavailable"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error placing bet: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Query Operations (Read Side)
@app.get("/api/v1/players/{player_id}/stats", response_model=PlayerStats)
async def get_player_stats(
    request: Request,
    player_id: str,
    claims: dict = Depends(verify_jwt_token)
):
    """
    Get player statistics - Routes to Query Service (PROTECTED)

    Requires: Valid JWT token in Authorization header
    Note: Users can only view their own stats (contains sensitive financial data)
    """
    try:
        logger.info(
            f"Get player stats - Auth check for requested player '{player_id}'"
        )

        check_player_matches_claims(player_id, claims, action="get_player_stats")

        response = await request.state.http_client.get(
            f"{QUERY_SERVICE_URL}/api/v1/players/{player_id}/stats",
            timeout=3.0,
        )

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player {player_id} not found"
            )
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to fetch player stats"
            )

    except TimeoutException:
        logger.error("Query service timeout")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Query service is not responding"
        )
    except RequestError as e:
        logger.error(f"Query service connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Query service is unavailable"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/api/v1/players/{player_id}/bets", response_model=dict)
async def get_player_bets(request: Request, player_id: str, claims: dict = Depends(verify_jwt_token)):
    """
    Forward request to Query Service to fetch player's bets, propagating X-Correlation-ID.
    """
    try:
        logger.info(
            f"Get player bets - Auth check for requested player '{player_id}'"
        )

        check_player_matches_claims(player_id, claims, action="get_player_bets")

        # Correlation ID handling: accept incoming or generate new
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())

        # Forward to Command Service, propagating correlation header and auth
        forward_headers = {"X-Correlation-ID": correlation_id}
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth_header:
            forward_headers["Authorization"] = auth_header

        response = await request.state.http_client.get(
            f"{QUERY_SERVICE_URL}/api/v1/players/{player_id}/bets",
            headers=forward_headers,
            timeout=3.0,
        )

        if response.status_code == 200:
            return Response(content=response.content, status_code=200, media_type="application/json", headers={"X-Correlation-ID": correlation_id} if correlation_id else None)
        elif response.status_code == 404:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Player {player_id} not found")
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch player bets")

    except Exception as e:
        logger.error(f"Unexpected error fetching player bets: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@app.get("/api/v1/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(request: Request, limit: int = 10):
    """
    Get leaderboard - Routes to Query Service
    """
    try:
        response = await request.state.http_client.get(
            f"{QUERY_SERVICE_URL}/api/v1/leaderboard",
            params={"limit": limit},
            timeout=3.0,
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to fetch leaderboard"
            )

    except TimeoutException:
        logger.error("Query service timeout")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Query service is not responding"
        )
    except RequestError as e:
        logger.error(f"Query service connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Query service is unavailable"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching leaderboard: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# User Service Routes (No authentication required for signup)
@app.post("/api/v1/users/signup", status_code=status.HTTP_201_CREATED)
async def signup_user(request: Request):
    """
    User signup - Routes to User Service (PUBLIC - no auth required)

    This allows new users to create accounts
    """
    try:
        body = await request.json()

        response = await request.state.http_client.post(
            f"{USER_SERVICE_URL}/api/v1/users/signup",
            json=body,
            timeout=10.0,
        )

        if response.status_code == 201:
            return response.json()
        else:
            error_detail = response.json().get("detail", "Failed to sign up user")
            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

    except TimeoutException:
        logger.error("User service timeout")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="User service is not responding"
        )
    except RequestError as e:
        logger.error(f"User service connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User service is unavailable"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error signing up user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/api/v1/users/{user_id}")
async def get_user(request: Request, user_id: str, claims: dict = Depends(verify_jwt_token)):
    """
    Get user information - Routes to User Service (PROTECTED)

    Users can view their own profile, admins can view any profile
    """
    try:
        # Allow owner or admin
        try:
            check_player_matches_claims(user_id, claims, action="get_user")
        except HTTPException:
            if not has_role(claims, "Admin"):
                raise

        response = await request.state.http_client.get(
            f"{USER_SERVICE_URL}/api/v1/users/{user_id}",
            timeout=5.0,
        )

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to fetch user"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.put("/api/v1/users/{user_id}")
async def update_user(request: Request, user_id: str, claims: dict = Depends(verify_jwt_token)):
    """
    Update user information - Routes to User Service (PROTECTED)

    Users can only update their own profile
    """
    try:
        check_player_matches_claims(user_id, claims, action="update_user")

        body = await request.json()

        response = await request.state.http_client.put(
            f"{USER_SERVICE_URL}/api/v1/users/{user_id}",
            json=body,
            timeout=5.0,
        )

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to update user"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.delete("/api/v1/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(request: Request, user_id: str, claims: dict = Depends(verify_jwt_token)):
    """
    Delete user - Routes to User Service (PROTECTED)

    Users can only delete their own account
    """
    try:
        check_player_matches_claims(user_id, claims, action="delete_user")

        response = await request.state.http_client.delete(
            f"{USER_SERVICE_URL}/api/v1/users/{user_id}",
            timeout=5.0,
        )

        if response.status_code == 204:
            return Response(status_code=204)
        elif response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to delete user"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/api/v1/users/{user_id}/wallet")
async def get_user_wallet(request: Request, user_id: str, claims: dict = Depends(verify_jwt_token)):
    """
    Get user wallet - Routes to User Service (PROTECTED)

    Users can view their own wallet, admins can view any wallet
    """
    try:
        # Allow owner or admin
        try:
            check_player_matches_claims(user_id, claims, action="get_wallet")
        except HTTPException:
            if not has_role(claims, "Admin"):
                raise

        response = await request.state.http_client.get(
            f"{USER_SERVICE_URL}/api/v1/users/{user_id}/wallet",
            timeout=5.0,
        )

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet not found for user {user_id}"
            )
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to fetch wallet"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching wallet: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


if __name__ == "__main__":
    uvicorn_run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
