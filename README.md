# Gaming Event System - CQRS with Kafka

A production-ready event-driven gaming platform demonstrating CQRS (Command Query Responsibility Segregation) pattern with Apache Kafka.

## Architecture Overview

This system implements a complete CQRS architecture with:
- **API Gateway**: Single entry point for external clients (BFF pattern)
- **Command Service**: Handles bet placement (write operations)
- **Query Service**: Provides player stats and leaderboards (read operations)
- **Event Processor**: Consumes Kafka events and updates Redis
- **Frontend**: React 19.2 + React Router 7 web application
- **Apache Kafka**: Event streaming platform (KRaft mode)
- **Redis**: Query-side data store

### Request Flow
```
Frontend → API Gateway → Command/Query Services → Kafka/Redis
                ↓
         CORS, Auth, Routing
```

## Technology Stack

### Backend
- Python 3.11
- FastAPI 0.104.1
- Apache Kafka 4.0.1 (KRaft mode - no Zookeeper)
- Redis 8.2.2

### Frontend
- React 19.2
- React Router 7
- TypeScript
- TailwindCSS
- Node.js 24.11.0

## Quick Start

### Prerequisites
- Docker & Docker Compose
- 8GB RAM minimum
- Ports 3000, 8000, 6379, 9092 available

### Running the System

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### Access Points

- **Frontend**: http://localhost:3000
- **API Gateway**: http://localhost:8000
- **API Gateway Docs**: http://localhost:8000/docs
- **Kafka**: localhost:9092
- **Redis**: localhost:6379

### API Documentation

- Command Service: http://localhost:5000/docs
- Query Service: http://localhost:5001/docs

## Frontend Features

The React frontend provides:
- **Play**: Interactive betting interface
- **Dashboard**: Real-time player statistics
- **Leaderboard**: Top players by balance
- **Health**: System status monitoring
- **Architecture**: System design visualization

## Development

### Running Tests

```bash
# Install test dependencies
pip install -r tests/requirements.txt

# Run integration tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=services
```

### Local Development

```bash
# Start backend services
docker-compose up -d kafka redis

# Run command service
cd services/command-service
pip install -r requirements.txt
uvicorn app:app --reload --port 5000

# Run query service
cd services/query-service
pip install -r requirements.txt
uvicorn app:app --reload --port 5001

# Run event processor
cd services/event-processor
pip install -r requirements.txt
python app.py

# Run frontend
cd services/frontend
npm install
npm run dev
```

## Event Flow

1. Client places bet via Command Service
2. Command Service publishes event to Kafka
3. Event Processor consumes event
4. Event Processor updates Redis
5. Query Service reads from Redis
6. Frontend displays updated data

## CQRS Benefits

- **Independent Scaling**: Scale read and write sides independently
- **Performance**: Optimized data models for each operation
- **Resilience**: Services can fail independently
- **Audit Trail**: All events stored in Kafka
- **Flexibility**: Easy to add new read models

## Kubernetes Deployment

Kubernetes manifests are available in the `k8s/` directory:

```bash
# Deploy to Kubernetes
kubectl apply -f k8s/

# Check status
kubectl get pods -n gaming-system
```

## License

MIT
