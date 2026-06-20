# API Rate Limiter & Gateway

A production-grade rate limiting middleware and API gateway built with FastAPI, Redis, and async Python. Implements three industry-standard rate limiting algorithms with a full async architecture, connection pooling, structured exception handling, and pluggable application patterns (middleware, decorator, context manager, descriptor).

Built as a portfolio project to demonstrate backend engineering depth for SDE1 roles at product-based companies — applying 2 years of automation/SRE experience at TCS toward distributed systems and API design.

---

## Algorithms

| Algorithm | Storage | Characteristics |
|---|---|---|
| **Fixed Window** | Redis string counter + TTL | Simple, cheap, has boundary burst edge case |
| **Sliding Window Log** | Redis sorted set (ZSET) | Accurate, no boundary burst, higher memory cost |
| **Token Bucket** | Redis hash | Allows controlled bursts, smooth long-term rate enforcement |

All three implement a common async interface (`RateLimiter` ABC) and are interchangeable via `RateLimiterFactory` — selected at runtime through configuration, no code changes required.

---

## Architecture

```
rate-limiter-api/
    src/rate_limiter/
        __init__.py            # public API surface
        enums.py                # Algorithm, RateLimitStatus, Scope
        models.py                # RateLimitRule, RateLimitKey, RateLimitResult
        exceptions.py            # exception hierarchy
        config.py                # Pydantic Settings, env-based configuration
        gateway.py                # FastAPI app, lifespan, app.state wiring
        middleware.py            # RateLimitMiddleware (BaseHTTPMiddleware)
        decorators.py            # @rate_limit function decorator
        descriptor.py            # RateLimitDescriptor (class method support)
        context.py                # RateLimitContext (async context manager)
        routers/
            admin.py              # status + manual reset endpoints
            proxy.py              # gateway passthrough demo
        limiters/
            base.py                # RateLimiter ABC (async interface)
            redis_base.py          # shared Redis connection pooling
            async_fixed_window.py
            async_sliding_window.py
            async_token_bucket.py
            factory.py             # RateLimiterFactory (Strategy + Factory pattern)
    tests/
    pyproject.toml
    .env.example
```

---

## Tech Stack

- **FastAPI** — async web framework, dependency injection, OpenAPI docs
- **Redis** (via `aioredis`) — distributed rate limit state, connection pooling
- **Pydantic Settings v2** — type-safe, environment-driven configuration with nested models and secrets handling
- **pytest / pytest-asyncio / fakeredis** — async-aware test suite (in progress)
- **structlog / prometheus_client** — structured logging and metrics (planned)
- **Docker** — containerized Redis for local development

---

## Key Design Decisions

**Why Redis over in-memory state?**
The project started with in-memory dict-based limiters protected by `threading.Lock` (Phase 2). These work for a single process but don't scale across multiple server instances. Migrating to Redis (Phase 4) gives distributed state — multiple gateway instances share the same rate limit counters, and Redis's single-threaded command execution provides atomicity for free, replacing the need for application-level locking.

**Why three different Redis data structures?**
Each algorithm's storage shape matches its semantics: fixed window needs only a counter (`INCR` + `EXPIRE`), sliding window needs an ordered log of timestamps (`ZADD` + `ZREMRANGEBYSCORE`), and token bucket needs two related fields read/written atomically together (`HSET`/`HGETALL`).

**Why `app.state` instead of a global variable for the limiter?**
The limiter is created once during FastAPI's `lifespan` startup and stored on `app.state`, not as a module-level global. This keeps state scoped to a specific app instance — critical for test isolation, since tests can spin up independent `FastAPI()` instances without shared state leaking between them.

**Why does middleware fetch the limiter from `app.state` instead of receiving it in `__init__`?**
`add_middleware()` is called before `lifespan` runs, so the limiter doesn't exist yet at registration time. Middleware fetches `request.app.state.limiter` fresh on every request — by the time any real request arrives, lifespan has already completed.

**Why three separate ways to apply rate limiting?**
- `RateLimitMiddleware` — global, applied once, protects every route by default (production pattern)
- `@rate_limit` decorator — per-function override for standalone endpoints needing different rules
- `RateLimitContext` — fine-grained control inside a function body, used heavily in the test suite
- `RateLimitDescriptor` — same as the decorator but for class-based method handlers, using the descriptor protocol (`__get__`) to bind `self` automatically

---

## Setup

```bash
# install dependencies
pip install -e ".[dev]"

# copy environment template and fill in values
cp .env.example .env

# start Redis locally via Docker
docker run -d --name redis-rl -p 6379:6379 redis:latest

# run the gateway
uvicorn rate_limiter.gateway:app --reload
```

### Environment variables (`.env`)

```dotenv
RL_ADMIN_KEY=your-admin-key-here
RL_REDIS__HOST=localhost
RL_REDIS__PORT=6379
RL_ALGORITHM=token_bucket
RL_DEBUG=false
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/admin/status` | Current algorithm and rate limit configuration |
| POST | `/admin/reset/{identifier}` | Manually reset rate limit state for an identifier |
| GET | `/proxy/{path}` | Gateway passthrough demonstration |

Every response includes rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 19
X-RateLimit-Reset: 1781990606.618586
Retry-After: 0
```

---

## Project Status

**Complete:**
- Phase 1 — Core data models, exception hierarchy, Pydantic Settings configuration
- Phase 2 — Three rate limiting algorithms (originally in-memory + threading.Lock)
- Phase 3 — Decorator, context manager, FastAPI middleware, descriptor protocol
- Phase 4 — Async Redis migration, connection pooling, FastAPI gateway with lifespan, admin/proxy routers

**In progress:**
- Phase 4.4 — Async generators and Server-Sent Events for live metrics streaming

**Planned:**
- Phase 5 — pytest suite with fixtures and fakeredis, structured logging (structlog), Prometheus metrics, Docker Compose deployment

---

## Concepts Demonstrated

`ABC` & abstract methods · Strategy + Factory design patterns · closures & decorator factories · `functools.wraps`/`update_wrapper` · descriptor protocol (`__get__`) · async/await & `asyncio` · Redis data structures (strings, sorted sets, hashes) · connection pooling · FastAPI dependency injection · ASGI middleware · lifespan events · Pydantic Settings v2 with nested models and secrets