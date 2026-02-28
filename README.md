# Dailymotion Moderation Tool

Backend services for video moderation, consisting of two microservices:

- **Moderation Queue**: Manages video moderation workflow (PostgreSQL)
- **Dailymotion API Proxy**: Proxies Dailymotion API with Redis caching

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│               Moderation Console UI (not included)              │
└─────────────────────────────────────────────────────────────────┘
                    │                           │
                    ▼                           ▼
┌───────────────────────────┐   ┌───────────────────────────────┐
│   Moderation Queue API    │   │   Dailymotion API Proxy       │
│       (port 8001)         │   │       (port 8002)             │
└───────────────────────────┘   └───────────────────────────────┘
            │                               │           │
            ▼                               ▼           │
┌───────────────────────────┐   ┌───────────────────┐  │
│       PostgreSQL          │   │       Redis       │  │
│       (port 5432)         │   │    (port 6379)    │  │
└───────────────────────────┘   └───────────────────┘  │
                                                       ▼
                                        ┌───────────────────────┐
                                        │   Dailymotion API     │
                                        │ (api.dailymotion.com) │
                                        └───────────────────────┘
```

## Prerequisites

- Docker
- Docker Compose

No other installation required.

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/plecart/Dailymotion-Moderation-tool.git
   cd Dailymotion-Moderation-tool
   ```

2. **Start all services**
   ```bash
   docker compose up -d
   ```

3. **Verify services are running**
   ```bash
   curl http://localhost:8001/health  # Moderation Queue
   curl http://localhost:8002/health  # Dailymotion API Proxy
   ```

## API Endpoints

### Moderation Queue (port 8001)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /add_video | No | Add video to moderation queue |
| GET | /get_video | Yes | Get next video to moderate |
| POST | /flag_video | Yes | Flag video as spam/not spam |
| GET | /stats | No | Get queue statistics |
| GET | /log_video/{video_id} | No | Get moderation history |
| GET | /health | No | Health check |

**Authentication**: Base64-encoded moderator name in `Authorization` header.

#### Examples

```bash
# Add a video to the queue
curl -X POST http://localhost:8001/add_video   -H "Content-Type: application/json"   -d '{"video_id": 123456}'

# Get next video (moderator: john.doe -> base64: am9obi5kb2U=)
curl http://localhost:8001/get_video   -H "Authorization: am9obi5kb2U="

# Flag video as spam
curl -X POST http://localhost:8001/flag_video   -H "Content-Type: application/json"   -H "Authorization: am9obi5kb2U="   -d '{"video_id": 123456, "status": "spam"}'

# Get statistics
curl http://localhost:8001/stats

# Get moderation history
curl http://localhost:8001/log_video/123456
```

### Dailymotion API Proxy (port 8002)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /get_video_info/{video_id} | Get video information |
| GET | /health | Health check |

**Note**: Video IDs ending with 404 (e.g., 1404, 10404) return HTTP 404.

#### Examples

```bash
# Get video info (cached via Redis)
curl http://localhost:8002/get_video_info/123456

# Video not found (404 rule)
curl http://localhost:8002/get_video_info/1404
```

## Running Tests

### Run all tests (both services)

```bash
# Moderation Queue tests (requires PostgreSQL running)
docker compose up -d postgres
cd moderation-queue
pip install -r requirements.txt
python -m pytest -v

# Dailymotion API Proxy tests (mocked, no dependencies)
cd dailymotion-api-proxy
pip install -r requirements.txt
python -m pytest -v
```

### Run tests in Docker

```bash
# Moderation Queue
docker compose exec moderation-queue python -m pytest -v

# Dailymotion API Proxy
docker compose exec dailymotion-api-proxy python -m pytest -v
```

## Project Structure

```
.
├── docker-compose.yml          # Service orchestration
├── .env                        # Environment variables
├── moderation-queue/           # Moderation Queue service
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pytest.ini
│   └── src/
│       ├── main.py             # FastAPI app
│       ├── config.py           # Settings
│       ├── dependencies.py     # DI providers
│       ├── exceptions.py       # Business exceptions
│       ├── database/           # DB connection & migrations
│       ├── models/             # Pydantic schemas & enums
│       ├── repositories/       # Raw SQL queries
│       ├── services/           # Business logic
│       └── routes/             # API endpoints
└── dailymotion-api-proxy/      # API Proxy service
    ├── Dockerfile
    ├── requirements.txt
    ├── pytest.ini
    └── src/
        ├── main.py             # FastAPI app
        ├── config.py           # Settings
        ├── exceptions.py       # Business exceptions
        ├── cache/              # Redis client
        ├── clients/            # HTTP client
        ├── models/             # Pydantic schemas
        ├── services/           # Business logic
        └── routes/             # API endpoints
```

## Technical Details

### Moderation Queue

- **Framework**: FastAPI
- **Database**: PostgreSQL 16 with asyncpg (no ORM)
- **Concurrency**: `SELECT FOR UPDATE SKIP LOCKED` for multi-moderator support
- **Migrations**: Custom SQL migration system

### Dailymotion API Proxy

- **Framework**: FastAPI
- **Cache**: Redis 7 with configurable TTL (default: 300s)
- **HTTP Client**: httpx async client
- **Fixed Video**: Always proxies video `x2m8jpp` per specification

## Environment Variables

| Variable | Service | Default | Description |
|----------|---------|---------|-------------|
| DATABASE_URL | moderation-queue | - | PostgreSQL connection string |
| REDIS_URL | dailymotion-api-proxy | redis://redis:6379 | Redis connection string |
| DAILYMOTION_API_BASE_URL | dailymotion-api-proxy | https://api.dailymotion.com | Dailymotion API URL |
| CACHE_TTL_SECONDS | dailymotion-api-proxy | 300 | Cache TTL in seconds |

## Stopping Services

```bash
docker compose down        # Stop containers
docker compose down -v     # Stop and remove volumes (clears data)
```
