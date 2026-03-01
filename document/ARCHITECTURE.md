# Architecture Schema

## Global Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Moderation Console UI                         │
│                      (Frontend - externe)                        │
└────────────┬──────────────────────────────┬─────────────────────┘
             │                              │
             │ REST API                     │ REST API
             │                              │
    ┌────────▼────────┐          ┌─────────▼──────────┐
    │  Moderation     │          │  Dailymotion API   │
    │  Queue API      │          │  Proxy             │
    │  (Port 8001)    │          │  (Port 8002)       │
    └────────┬────────┘          └──┬──────────────┬──┘
             │                      │              │
    ┌────────▼────────┐    ┌───────▼──────┐  ┌────▼──────────────┐
    │   PostgreSQL    │    │    Redis     │  │  Dailymotion API  │
    │   (Port 5432)   │    │  (Port 6379) │  │   (Externe)       │
    └─────────────────┘    └──────────────┘  └───────────────────┘
```

## Layered Architecture

### Moderation Queue

```
┌───────────────────────────────────────────────────┐
│  Routes          (FastAPI endpoints)               │
│  add_video · get_video · flag_video · stats · log  │
├───────────────────────────────────────────────────┤
│  Dependencies    (DI)                              │
│  DB connection · base64 auth                       │
├───────────────────────────────────────────────────┤
│  Services        (Business logic)                  │
│  FIFO assignment · advisory locks · flag logic     │
├───────────────────────────────────────────────────┤
│  Repositories    (Data access)                     │
│  Raw SQL · asyncpg · no ORM                        │
├───────────────────────────────────────────────────┤
│  PostgreSQL 16   (asyncpg pool)                    │
│  SQL migrations at startup                         │
└───────────────────────────────────────────────────┘
```

### Dailymotion API Proxy

```
┌───────────────────────────────────────────────────┐
│  Routes          (FastAPI endpoint)                │
│  get_video_info/{video_id}                         │
├───────────────────────────────────────────────────┤
│  Services        (Business logic)                  │
│  404 rule · cache read-through · error handling    │
├──────────────────────┬────────────────────────────┤
│  Cache               │  HTTP Client               │
│  Redis best-effort   │  httpx AsyncClient          │
├──────────────────────┼────────────────────────────┤
│  Redis 7             │  Dailymotion API            │
└──────────────────────┴────────────────────────────┘
```

## Data Flows

### Add a video

```
POST /add_video {"video_id": 123456}
       │
       ▼
  Pydantic validation → Service → INSERT (status='pending') → PostgreSQL
       │
       ▼
  HTTP 201
```

### Get next video (moderator)

```
GET /get_video + Authorization: base64(moderator)
       │
       ▼
  Decode base64 → Advisory lock (per-moderator)
       │
       ├─ Already assigned? → return same video
       └─ SELECT FOR UPDATE SKIP LOCKED → assign next FIFO → PostgreSQL
       │
       ▼
  HTTP 200 {"video_id": ...}
```

### Get video info (proxy)

```
GET /get_video_info/123456
       │
       ├─ video_id ends with 404? → HTTP 404
       │
       ├─ Redis cache hit? → return cached data
       │
       └─ Cache miss → GET Dailymotion API → cache (TTL) → return
```

### Flag a video

```
POST /flag_video {"video_id": 123456, "status": "spam"} + Authorization
       │
       ▼
  Validate: exists? pending? assigned to moderator?
       │
       ▼
  Transaction:
    UPDATE videos WHERE status='pending' AND assigned_to=moderator
    INSERT moderation_logs
       │
       ▼
  HTTP 200 {"video_id": 123456, "status": "spam"}
```

## Database Schema

```
┌──────────────────────────┐         ┌──────────────────────────┐
│         videos            │         │     moderation_logs       │
├──────────────────────────┤         ├──────────────────────────┤
│ id          SERIAL PK     │    ┌──►│ id          SERIAL PK     │
│ video_id    BIGINT UNIQUE ├────┘   │ video_id    BIGINT FK     │
│ status      VARCHAR(20)   │        │ status      VARCHAR(20)   │
│ assigned_to VARCHAR(255)  │        │ moderator   VARCHAR(255)  │
│ created_at  TIMESTAMP     │        │ created_at  TIMESTAMP     │
│ updated_at  TIMESTAMP     │        └──────────────────────────┘
└──────────────────────────┘
```

## Docker Compose

| Service | Image | Port |
|---|---|---|
| postgres | postgres:16-alpine | 5432 |
| redis | redis:7-alpine | 6379 |
| moderation-queue | Python 3.12 + uvicorn | 8001 → 8000 |
| dailymotion-api-proxy | Python 3.12 + uvicorn | 8002 → 8000 |

## Tech Stack

- **Python 3.12**, **FastAPI** (routing + DI only)
- **PostgreSQL 16** + asyncpg (raw SQL, no ORM)
- **Redis 7** + redis.asyncio (best-effort cache)
- **httpx** (async HTTP client)
- **Docker Compose** (4 services, healthchecks)
- **pytest** + pytest-asyncio (AAA pattern)
