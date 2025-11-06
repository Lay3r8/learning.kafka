# API Gateway (Experience API Layer)

## Overview

The API Gateway implements the **Backend For Frontend (BFF)** pattern, serving as the single entry point for all external clients (frontend applications).

## Architecture Pattern

```
Frontend → API Gateway → Internal Services
                ↓
         [Command Service]
         [Query Service]
```

## Responsibilities

### 🛡️ Security & CORS
- **Single CORS configuration point** - No CORS needed in internal services
- **Request validation** - Centralized input validation
- **Rate limiting** - Protect backend services (future)
- **Authentication** - JWT validation (future Phase 2)

### 🔀 Request Routing
- Routes `/api/v1/bets` → Command Service
- Routes `/api/v1/players/*` → Query Service
- Routes `/api/v1/leaderboard` → Query Service

### 🔧 API Transformation
- Adapts internal API contracts to frontend needs
- Adds client metadata (IP address, timestamps)
- Aggregates multiple backend calls if needed

### 📊 Monitoring
- Health checks for all backend services
- Gateway-level logging and metrics
- Request/response timing

## Endpoints

### Health Check
```http
GET /health
```
Returns gateway status and backend service health.

### Place Bet (Command)
```http
POST /api/v1/bets
Content-Type: application/json

{
  "player_id": "player123",
  "game_type": "slots",
  "amount": 100.0,
  "session_id": "session_abc",
  "ip_address": "192.168.1.1"  // Optional - auto-added by gateway
}
```

### Get Player Stats (Query)
```http
GET /api/v1/players/{player_id}/stats
```

### Get Leaderboard (Query)
```http
GET /api/v1/leaderboard?limit=50
```

## Configuration

Environment variables:

```bash
COMMAND_SERVICE_URL=http://command-service:5000
QUERY_SERVICE_URL=http://query-service:5001
```

## Benefits

1. **Security**: Internal services not exposed to internet
2. **Flexibility**: Can change internal services without affecting frontend
3. **Performance**: Can add caching layer at gateway
4. **Monitoring**: Centralized logging and metrics
5. **Versioning**: API version management in one place
6. **CORS**: Configured once instead of N times

## Future Enhancements (Phase 2)

- [ ] OAuth2 authentication
- [ ] Rate limiting per client
- [ ] Response caching (Redis)
- [ ] Request/response logging to Kafka
- [ ] API versioning (/v1, /v2)
- [ ] GraphQL endpoint
- [ ] WebSocket support for real-time updates

## Development

```bash
# Local development
cd services/api-gateway
pip install -r requirements.txt
python app.py

# Access
curl http://localhost:8000/health
```

## Docker

```bash
docker build -t api-gateway .
docker run -p 8000:8000 \
  -e COMMAND_SERVICE_URL=http://command-service:5000 \
  -e QUERY_SERVICE_URL=http://query-service:5001 \
  api-gateway
```
