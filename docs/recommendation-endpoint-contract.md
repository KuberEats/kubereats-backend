# Recommendation Endpoint Contract

Frontend base API URL:

```text
https://api.kubereats.click
```

Recommendation public prefix:

```text
/recommend
```

This document is an inspection of `origin/module/recommend` only. It does not
deploy recommendation-service, change Kubernetes manifests, change GCP Load
Balancer settings, or modify secrets.

## Service Inventory

| Item | Current state |
| --- | --- |
| Source branch | `origin/module/recommend` |
| Service path | Branch-root FastAPI app under `app/` |
| App entrypoint | `app/main.py` |
| Framework | FastAPI |
| Router file | `app/routes/recommendation_route.py` |
| Current router prefix | `/recommendations` |
| Dockerfile | `Dockerfile.dev` only |
| Container port | `8000` |
| Startup command | `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` |
| Health endpoint | `GET /health`, plus `GET /health-check` |
| OpenAPI docs | FastAPI defaults: `/docs`, `/redoc`, `/openapi.json` |
| Database | Required for recommendation endpoints through `DATABASE_URL` |
| External API | Optional OpenRouter for prompt parsing and reranking; falls back locally if missing/failing |
| Redis/cache/queue | No Redis, cache, or queue dependency found in recommendation source |
| Tests | Vitest API tests under `test/`; CI starts Postgres, seeds data, starts uvicorn, then runs `npm test` |

## Current Routes

These are the actual routes parsed from `origin/module/recommend`.

| Method | Actual route | Handler/function | Auth required? | DB required? | External API required? | Notes |
| ------ | ------------ | ---------------- | -------------- | ------------ | ---------------------- | ----- |
| GET | `/` | `root` | No | No | No | Service root message |
| GET | `/health` | `health_check` | No | No | No | Kubernetes health probe path |
| GET | `/health-check` | `health_check_alias` | No | No | No | Alias of `/health` |
| GET | `/recommendations/grafana-check` | `grafana_check` | No | No | No | In-memory recommendation/OpenRouter metrics snapshot |
| POST | `/recommendations/merchants` | `recommend_merchants_by_prompt` | No | Yes | Optional | Prompt-based merchant recommendations; OpenRouter may be used if configured |
| GET | `/recommendations/merchants` | `recommend_merchants` | No | Yes | Optional | Query-style merchant recommendations with `userId`, optional `campus`, `limit` |
| POST | `/recommendations/menus` | `recommend_menus_by_prompt` | No | Yes | Optional | Prompt-based menu recommendations; optional `merchantId` in body |
| GET | `/recommendations/menus` | `recommend_menus` | No | Yes | Optional | Query-style menu recommendations with `userId`, optional `campus`, `merchantId`, `limit` |

Not currently present:

```text
GET  /recommend/health
GET  /recommend/items
GET  /recommend/merchants
GET  /recommend/users/{user_id}
POST /recommend/generate
POST /recommend/feedback
GET  /api/recommend/*
GET  /api/recommand/*
GET  /recommand/*
```

## Recommended Public Routes

Use current functionality only; do not invent unavailable features.

| Purpose | Current endpoint | Recommended public endpoint | Method | Needs backend change? | Needs LB rewrite? | Frontend action |
| ------- | ---------------- | --------------------------- | ------ | --------------------- | ----------------- | --------------- |
| Service health | `/health` | `/recommend/health` | GET | Yes | No if backend supports `/recommend/health`; otherwise rewrite needed | Use `/recommend/health` after backend route update |
| Metrics/Grafana check | `/recommendations/grafana-check` | `/recommend/grafana-check` | GET | Yes | No if backend supports `/recommend/*`; otherwise rewrite needed | Use `/recommend/grafana-check` only for internal/admin diagnostics |
| Merchant recommendations, prompt body | `/recommendations/merchants` | `/recommend/merchants` | POST | Yes | No if backend supports `/recommend/*`; otherwise rewrite needed | Replace `/recommendations/merchants` with `/recommend/merchants` |
| Merchant recommendations, query style | `/recommendations/merchants?userId=...` | `/recommend/merchants?userId=...` | GET | Yes | No if backend supports `/recommend/*`; otherwise rewrite needed | Replace `/recommendations/merchants` with `/recommend/merchants` |
| Menu recommendations, prompt body | `/recommendations/menus` | `/recommend/menus` | POST | Yes | No if backend supports `/recommend/*`; otherwise rewrite needed | Replace `/recommendations/menus` with `/recommend/menus` |
| Menu recommendations, query style | `/recommendations/menus?userId=...` | `/recommend/menus?userId=...` | GET | Yes | No if backend supports `/recommend/*`; otherwise rewrite needed | Replace `/recommendations/menus` with `/recommend/menus` |
| Item recommendations | Not implemented | `/recommend/items` | GET | Yes, feature not implemented | No if implemented under `/recommend/*` | Do not call until backend implements it |
| User-specific recommendations | Not implemented | `/recommend/users/{user_id}` | GET | Yes, feature not implemented | No if implemented under `/recommend/*` | Do not call until backend implements it |
| Generate recommendations | Not implemented as `/generate` | `/recommend/generate` | POST | Yes, feature/route not implemented | No if implemented under `/recommend/*` | Do not call until backend implements it |
| Recommendation feedback | Not implemented | `/recommend/feedback` | POST | Yes, feature not implemented | No if implemented under `/recommend/*` | Do not call until backend implements it |

## Contract Decision

The service does **not** currently comply with the public API contract because
it exposes recommendation endpoints under:

```text
/recommendations/*
```

The target contract is:

```text
/recommend/*
```

## GCP LB Path Rewrite

If the GCP URL map is configured as:

```text
api.kubereats.click /recommend/* -> recommendation-backend
```

the current backend cannot directly consume `/recommend/*`, because it only has
`/recommendations/*` plus root health routes.

### Option A: Backend Supports Prefix Directly

Recommended. Update the FastAPI app to expose:

```text
GET  /recommend/health
GET  /recommend/grafana-check
GET  /recommend/merchants
POST /recommend/merchants
GET  /recommend/menus
POST /recommend/menus
```

Then GCP LB can forward `/recommend/*` unchanged:

```text
/recommend/* -> recommendation-backend -> recommendation-service
```

No GCP URL rewrite required.

### Option B: GCP LB Rewrite

Temporary fallback only. Keep external URLs as:

```text
/recommend/*
```

and rewrite selected paths to existing backend routes:

```text
/recommend/health -> /health
/recommend/grafana-check -> /recommendations/grafana-check
/recommend/merchants -> /recommendations/merchants
/recommend/menus -> /recommendations/menus
```

This is less preferred because routing behavior lives in the load balancer
instead of the service contract.

## Typo Check

Search commands run:

```bash
grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.pytest_cache --exclude-dir=.ruff_cache "recommand" . || true
grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.pytest_cache --exclude-dir=.ruff_cache "recommend" . || true
git grep -n "recommand" origin/module/recommend -- . || true
git grep -n "recommend" origin/module/recommend -- . || true
```

Findings:

| Spelling | Location | Notes |
| --- | --- | --- |
| `recommand` | `git log origin/module/recommend`: commit `6348da4 recommand template no api` | Typo appears in commit history only |
| `recommend` | Branch name `origin/module/recommend` | Accepted source branch name |
| `recommendations` | Current route prefix `/recommendations` | Functional but does not match public `/recommend/*` contract |
| `recommendation-service` | Deploy manifests and image name | Recommended service/image name |

Recommended naming:

```text
recommendation-service
/recommend/*
ghcr.io/kubereats/recommendation-service:<tag>
```

Avoid:

```text
recommand
/recommand/*
/api/recommend/*
/api/recommand/*
```

## Frontend Instructions

Base URL:

```text
https://api.kubereats.click
```

After backend route alignment, call:

```text
GET  /recommend/health
GET  /recommend/merchants?userId=2&campus=竹科&limit=3
POST /recommend/merchants
GET  /recommend/menus?userId=2&campus=竹科&merchantId=3&limit=5
POST /recommend/menus
```

Do not call:

```text
/recommand/*
/api/recommend/*
/api/recommand/*
```

`/recommendations/*` is the current backend route, not the target public route.

## GCP LB Mapping Recommendation

Target state:

```text
/recommend/* -> recommendation-backend -> recommendation-service
```

No GCP rewrite after the backend supports `/recommend/*` directly.
