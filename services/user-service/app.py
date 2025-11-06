"""
User Service - User Management & Auth0 Integration

Responsibilities:
- User CRUD operations
- Auth0 user signup and deletion
- Wallet initialization
- Publishing user events to Kafka
- PostgreSQL as source of truth for user data
"""
from logging import basicConfig, getLogger, INFO, StreamHandler
from sys import stdout
from os import getenv
from uuid import uuid4
from datetime import datetime
from decimal import Decimal
from typing import Optional
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from kafka import KafkaProducer
from kafka.errors import KafkaError
import json
from auth0.authentication import Database, GetToken
from auth0.management import Auth0


# Environment Configuration
KAFKA_BOOTSTRAP_SERVERS = getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_USER_TOPIC = getenv("KAFKA_USER_TOPIC")
POSTGRES_HOST = getenv("POSTGRES_HOST")
POSTGRES_PORT = int(getenv("POSTGRES_PORT"))
POSTGRES_DB = getenv("POSTGRES_DB")
POSTGRES_USER = getenv("POSTGRES_USER")
POSTGRES_PASSWORD = getenv("POSTGRES_PASSWORD")

# Auth0 Configuration
AUTH0_DOMAIN = getenv("AUTH0_DOMAIN")
AUTH0_MGMT_CLIENT_ID = getenv("AUTH0_MGMT_CLIENT_ID")
AUTH0_MGMT_CLIENT_SECRET = getenv("AUTH0_MGMT_CLIENT_SECRET")
AUTH0_CONNECTION = getenv("AUTH0_CONNECTION")

if not all([AUTH0_DOMAIN, AUTH0_MGMT_CLIENT_ID, AUTH0_MGMT_CLIENT_SECRET]):
    raise ValueError("AUTH0_DOMAIN, AUTH0_MGMT_CLIENT_ID, and AUTH0_MGMT_CLIENT_SECRET are required")

# Logging
basicConfig(
    level=INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[StreamHandler(stdout)]
)
logger = getLogger(__name__)

app = FastAPI(
    title="User Service",
    description="User Management & Auth0 Integration",
    version="1.0.0"
)

# Pydantic Models
class UserSignupRequest(BaseModel):
    email: EmailStr
    password: str
    username: Optional[str] = None

class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None

class UserResponse(BaseModel):
    user_id: str
    email: str
    username: Optional[str]
    created_at: str
    is_active: bool

class WalletResponse(BaseModel):
    wallet_id: int
    user_id: str
    balance: Decimal
    currency: str


# AsyncConnectionPool for PostgreSQL (psycopg 3)
db_pool: Optional[AsyncConnectionPool] = None

async def get_db_pool() -> AsyncConnectionPool:
    """Get or create AsyncConnectionPool for PostgreSQL"""
    global db_pool
    if db_pool is None:
        connection_string = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        db_pool = AsyncConnectionPool(
            connection_string,
            min_size=2,
            max_size=10,
            timeout=30.0,
            kwargs={"row_factory": dict_row}
        )
        logger.info("AsyncConnectionPool created")
    return db_pool


async def startup_event():
    """Initialize connection pool on startup"""
    await get_db_pool()
    logger.info("Database connection pool initialized")


async def shutdown_event():
    """Close connection pool on shutdown"""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database connection pool closed")


# Register lifecycle events
@app.on_event("startup")
async def on_startup():
    await startup_event()


@app.on_event("shutdown")
async def on_shutdown():
    await shutdown_event()


# Kafka Producer
kafka_producer = None

def get_kafka_producer():
    """Get or create Kafka producer"""
    global kafka_producer
    if kafka_producer is None:
        try:
            kafka_producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3
            )
            logger.info("Kafka producer initialized")
        except Exception as e:
            logger.error(f"Failed to create Kafka producer: {e}")
            raise
    return kafka_producer


def publish_user_event(event_type: str, user_id: str, data: dict, correlation_id: str):
    """Publish user event to Kafka"""
    try:
        event = {
            "event_id": str(uuid4()),
            "event_type": event_type,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id,
            "data": data
        }

        producer = get_kafka_producer()
        future = producer.send(
            KAFKA_USER_TOPIC,
            key=user_id,
            value=event,
            headers=[("X-Correlation-ID", correlation_id.encode("utf-8"))]
        )

        # Wait for acknowledgment
        record_metadata = future.get(timeout=10)
        logger.info(
            f"User event published: {event_type}",
            extra={
                "event_id": event["event_id"],
                "user_id": user_id,
                "topic": record_metadata.topic,
                "partition": record_metadata.partition,
                "offset": record_metadata.offset
            }
        )
    except KafkaError as e:
        logger.error(f"Failed to publish user event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to publish user event"
        )


# Auth0 Integration
def get_mgmt_api_token() -> str:
    """Get Auth0 Management API token"""
    try:
        get_token = GetToken(AUTH0_DOMAIN, AUTH0_MGMT_CLIENT_ID, client_secret=AUTH0_MGMT_CLIENT_SECRET)
        token_response = get_token.client_credentials(f'https://{AUTH0_DOMAIN}/api/v2/')
        return token_response['access_token']
    except Exception as e:
        logger.error(f"Failed to get Auth0 Management API token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to authenticate with Auth0: {str(e)}"
        )


def create_auth0_user(email: str, password: str) -> str:
    """Create user in Auth0 and return user_id (sub)"""
    try:
        logger.info(f"Creating Auth0 user: {email}")

        # Sign up user using Database authentication
        database = Database(AUTH0_DOMAIN, AUTH0_MGMT_CLIENT_ID)
        response = database.signup(
            email=email,
            password=password,
            connection=AUTH0_CONNECTION
        )
        logger.info(f"Auth0 signup response: {response}")

        # The signup response includes _id which we can use to construct the user_id
        # Auth0 database connection user_id format: auth0|{_id}
        if '_id' in response:
            user_id = f"auth0|{response['_id']}"
            logger.info(f"Auth0 user created successfully: {user_id}")
            return user_id
        else:
            raise Exception(f"Unexpected signup response format: {response}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth0 user creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Auth0 user: {str(e)}"
        )


def delete_auth0_user(user_id: str):
    """Delete user from Auth0 using Management API"""
    try:
        mgmt_token = get_mgmt_api_token()
        auth0_mgmt = Auth0(AUTH0_DOMAIN, mgmt_token)
        auth0_mgmt.users.delete(user_id)
        logger.info(f"Auth0 user deleted: {user_id}")
    except Exception as e:
        logger.error(f"Auth0 user deletion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete Auth0 user: {str(e)}"
        )


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "user-service",
        "database": "connected"  # Could add actual DB check here
    }


@app.post("/api/v1/users/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup_user(request: UserSignupRequest):
    """
    Sign up a new user

    1. Create user in Auth0
    2. Create user record in PostgreSQL
    3. Initialize wallet with 0 balance
    4. Publish USER_REGISTERED event
    """
    correlation_id = str(uuid4())
    pool = await get_db_pool()

    try:
        # Step 1: Create user in Auth0
        logger.info(f"Creating Auth0 user: {request.email}")
        auth0_user_id = create_auth0_user(request.email, request.password)

        # Step 2: Create user in PostgreSQL using async connection
        async with pool.connection() as conn:
            async with conn.cursor() as cursor:
                # Insert user
                await cursor.execute(
                    """
                    INSERT INTO users (user_id, email, username, is_active)
                    VALUES (%s, %s, %s, %s)
                    RETURNING user_id, email, username, created_at, is_active
                    """,
                    (auth0_user_id, request.email, request.username or request.email.split('@')[0], True)
                )
                user_row = await cursor.fetchone()

                # Step 3: Initialize wallet
                await cursor.execute(
                    """
                    INSERT INTO wallets (user_id, balance, currency)
                    VALUES (%s, %s, %s)
                    RETURNING wallet_id
                    """,
                    (auth0_user_id, Decimal("0.00"), "USD")
                )
                wallet_row = await cursor.fetchone()

                # Record initial transaction
                await cursor.execute(
                    """
                    INSERT INTO wallet_transactions (wallet_id, amount, transaction_type, description)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (wallet_row['wallet_id'], Decimal("0.00"), "INITIAL", "Wallet initialized")
                )

                await conn.commit()

        # Step 4: Publish USER_REGISTERED event
        publish_user_event(
            event_type="USER_REGISTERED",
            user_id=auth0_user_id,
            data={
                "email": request.email,
                "username": user_row['username'],
                "wallet_id": wallet_row['wallet_id']
            },
            correlation_id=correlation_id
        )

        logger.info(f"User registered successfully: {auth0_user_id}")

        return UserResponse(
            user_id=user_row['user_id'],
            email=user_row['email'],
            username=user_row['username'],
            created_at=user_row['created_at'].isoformat(),
            is_active=user_row['is_active']
        )

    except psycopg.errors.UniqueViolation as e:
        logger.error(f"User already exists: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )
    except Exception as e:
        logger.error(f"User signup failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User signup failed: {str(e)}"
        )


@app.get("/api/v1/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get user by ID"""
    pool = await get_db_pool()

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT user_id, email, username, created_at, is_active FROM users WHERE user_id = %s",
                    (user_id,)
                )
                user = await cursor.fetchone()

                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="User not found"
                    )

                return UserResponse(
                    user_id=user['user_id'],
                    email=user['email'],
                    username=user['username'],
                    created_at=user['created_at'].isoformat(),
                    is_active=user['is_active']
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.put("/api/v1/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, request: UserUpdateRequest):
    """Update user information"""
    correlation_id = str(uuid4())
    pool = await get_db_pool()

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cursor:
                # Build dynamic UPDATE query
                update_fields = []
                params = []

                if request.username is not None:
                    update_fields.append("username = %s")
                    params.append(request.username)

                if request.email is not None:
                    update_fields.append("email = %s")
                    params.append(request.email)

                if not update_fields:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No fields to update"
                    )

                params.append(user_id)
                query = f"""
                    UPDATE users
                    SET {', '.join(update_fields)}
                    WHERE user_id = %s
                    RETURNING user_id, email, username, created_at, is_active
                """

                await cursor.execute(query, params)
                user = await cursor.fetchone()

                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="User not found"
                    )

                await conn.commit()

                # Publish USER_UPDATED event
                publish_user_event(
                    event_type="USER_UPDATED",
                    user_id=user_id,
                    data={
                        "email": user['email'],
                        "username": user['username']
                    },
                    correlation_id=correlation_id
                )

                return UserResponse(
                    user_id=user['user_id'],
                    email=user['email'],
                    username=user['username'],
                    created_at=user['created_at'].isoformat(),
                    is_active=user['is_active']
                )
    except HTTPException:
        raise
    except psycopg.errors.UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already exists"
        )
    except Exception as e:
        logger.error(f"Error updating user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.delete("/api/v1/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str):
    """
    Delete user

    1. Delete from Auth0
    2. Soft delete in PostgreSQL (set is_active = false)
    3. Publish USER_DELETED event
    """
    correlation_id = str(uuid4())
    pool = await get_db_pool()

    try:
        # Step 1: Delete from Auth0
        delete_auth0_user(user_id)

        # Step 2: Soft delete in PostgreSQL
        async with pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE users SET is_active = false WHERE user_id = %s RETURNING email, username",
                    (user_id,)
                )
                user = await cursor.fetchone()

                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="User not found"
                    )

                await conn.commit()

                # Step 3: Publish USER_DELETED event
                publish_user_event(
                    event_type="USER_DELETED",
                    user_id=user_id,
                    data={
                        "email": user['email'],
                        "username": user['username']
                    },
                    correlation_id=correlation_id
                )

                logger.info(f"User deleted successfully: {user_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/api/v1/users/{user_id}/wallet", response_model=WalletResponse)
async def get_user_wallet(user_id: str):
    """Get user's wallet information"""
    pool = await get_db_pool()

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT wallet_id, user_id, balance, currency FROM wallets WHERE user_id = %s",
                    (user_id,)
                )
                wallet = await cursor.fetchone()

                if not wallet:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Wallet not found"
                    )

                return WalletResponse(
                    wallet_id=wallet['wallet_id'],
                    user_id=wallet['user_id'],
                    balance=wallet['balance'],
                    currency=wallet['currency']
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching wallet: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5002, log_level="info")
