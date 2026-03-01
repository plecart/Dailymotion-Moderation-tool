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

## Testing Multi-Moderator Scenario

This section demonstrates the multi-moderator behavior as per specification.

### Setup: Add multiple videos

```bash
curl -X POST http://localhost:8001/add_video -H "Content-Type: application/json" -d '{"video_id": 1001}'
curl -X POST http://localhost:8001/add_video -H "Content-Type: application/json" -d '{"video_id": 1002}'
```

### Test 1: Same moderator gets same video

```bash
# Moderator: john.doe (base64: am9obi5kb2U=)
curl http://localhost:8001/get_video -H "Authorization: am9obi5kb2U="
# Returns: {"video_id": 1001}

# Same moderator, same request -> same video
curl http://localhost:8001/get_video -H "Authorization: am9obi5kb2U="
# Returns: {"video_id": 1001}
```

### Test 2: Different moderators get different videos

```bash
# Moderator: john.doe (base64: am9obi5kb2U=)
curl http://localhost:8001/get_video -H "Authorization: am9obi5kb2U="
# Returns: {"video_id": 1001}

# Moderator: jane.smith (base64: amFuZS5zbWl0aA==)
curl http://localhost:8001/get_video -H "Authorization: amFuZS5zbWl0aA=="
# Returns: {"video_id": 1002}
```

### Test 3: After flagging, moderator gets next video

```bash
# john.doe flags video 1001
curl -X POST http://localhost:8001/flag_video -H "Content-Type: application/json" -H "Authorization: am9obi5kb2U=" -d '{"video_id": 1001, "status": "spam"}'

# john.doe now gets next pending video
curl http://localhost:8001/get_video -H "Authorization: am9obi5kb2U="
# Returns: next pending video (or 404 if none available)
```

### Test 4: Verify with stats and logs

```bash
# Check queue statistics
curl http://localhost:8001/stats
# Returns: {"total_pending_videos": 1, "total_spam_videos": 1, "total_not_spam_videos": 0}

# Check moderation history for video 1001
curl http://localhost:8001/log_video/1001
# Returns: [{"date": "2026-02-28T18:43:02.131404", "status": "spam", "moderator": "john.doe"}]
```

## Running Tests

### Run tests in Docker (recommended)

```bash
# Start services first
docker compose up -d

# Moderation Queue
docker compose exec moderation-queue python -m pytest -v

# Dailymotion API Proxy
docker compose exec dailymotion-api-proxy python -m pytest -v
```

### Run tests locally

```bash
# Moderation Queue (requires a running PostgreSQL instance)
# Tests use a real database connection (not mocked) — defaults to localhost:5432
docker compose up -d postgres
cd moderation-queue
pip install -r requirements.txt
python -m pytest -v

# Dailymotion API Proxy (fully mocked, no external dependencies)
cd dailymotion-api-proxy
pip install -r requirements.txt
python -m pytest -v
```

## Project Structure

```
.
├── docker-compose.yml          # Service orchestration
├── .env                        # Environment variables
├── README.md                   # This file
├── document/
│   ├── ARCHITECTURE.md         # Architecture schema
│   └── moderation_tool.md      # Technical test specification
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
- **Fixed Video**: Proxies a fixed video ID (default: `x2m8jpp` in code, `.env` uses `x9zxn76` for testing, configurable via `DAILYMOTION_FIXED_VIDEO_ID`)

## Environment Variables

| Variable | Service | Default | Description |
|----------|---------|---------|-------------|
| POSTGRES_USER | postgres (Docker) | - | PostgreSQL user |
| POSTGRES_PASSWORD | postgres (Docker) | - | PostgreSQL password |
| POSTGRES_DB | postgres (Docker) | - | PostgreSQL database name |
| DATABASE_URL | moderation-queue | - | PostgreSQL connection string |
| DATABASE_POOL_MIN_SIZE | moderation-queue | 2 | Minimum connections in pool |
| DATABASE_POOL_MAX_SIZE | moderation-queue | 10 | Maximum connections in pool |
| REDIS_URL | dailymotion-api-proxy | redis://localhost:6379 | Redis connection string |
| DAILYMOTION_API_BASE_URL | dailymotion-api-proxy | https://api.dailymotion.com | Dailymotion API URL |
| CACHE_TTL_SECONDS | dailymotion-api-proxy | 300 | Cache TTL in seconds |
| DAILYMOTION_FIXED_VIDEO_ID | dailymotion-api-proxy | x2m8jpp (x9zxn76 in committed .env) | Fixed video ID to fetch |

## Stopping Services

```bash
docker compose down        # Stop containers
docker compose down -v     # Stop and remove volumes (clears data)
```
