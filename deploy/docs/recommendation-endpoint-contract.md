# Recommendation Endpoint Contract

Frontend base API URL:

```text
https://api.kubereats.click
```

Recommendation public prefix:

```text
/recommend
```

This document summarizes the current `origin/module/recommend` API surface and
the target GCP Load Balancer route contract. It does not deploy the service,
change Kubernetes manifests, change GCP Load Balancer settings, or modify
secrets.

## Current Service State

| Item | Current state |
| --- | --- |
| Source branch | `origin/module/recommend` |
| App entrypoint | `app/main.py` |
| Framework | FastAPI |
| Current router prefix | `/recommendations` |
| Dockerfile | `Dockerfile.dev` only |
| Container port | `8000` |
| Startup command | `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` |
| Kubernetes probe path in current manifests | `/health` |
| Database | Required through `DATABASE_URL` for recommendation endpoints |
| External API | Optional OpenRouter via `OPENROUTER_API_KEY`; local fallback exists |
| Redis/cache/queue | Not found in current recommendation source |
| Tests | Vitest API tests under `test/` |

## Current Routes

| Method | Actual route | Handler/function | Auth required? | DB required? | External API required? | Notes |
| ------ | ------------ | ---------------- | -------------- | ------------ | ---------------------- | ----- |
| GET | `/` | `root` | No | No | No | Root message |
| GET | `/health` | `health_check` | No | No | No | Existing probe path |
| GET | `/health-check` | `health_check_alias` | No | No | No | Health alias |
| GET | `/recommendations/grafana-check` | `grafana_check` | No | No | No | In-memory metrics snapshot |
| GET | `/recommendations/merchants` | `recommend_merchants` | No | Yes | Optional | Query-style merchant recommendations |
| POST | `/recommendations/merchants` | `recommend_merchants_by_prompt` | No | Yes | Optional | Prompt-based merchant recommendations |
| GET | `/recommendations/menus` | `recommend_menus` | No | Yes | Optional | Query-style menu recommendations |
| POST | `/recommendations/menus` | `recommend_menus_by_prompt` | No | Yes | Optional | Prompt-based menu recommendations |

The backend currently has no `/recommend/*`, `/recommand/*`,
`/api/recommend/*`, or `/api/recommand/*` routes.

## Recommended Public Routes

Use existing functionality only:

| Purpose | Current endpoint | Recommended public endpoint | Method | Needs backend change? | Needs LB rewrite? | Frontend action |
| ------- | ---------------- | --------------------------- | ------ | --------------------- | ----------------- | --------------- |
| Health | `/health` | `/recommend/health` | GET | Yes | No after backend route update | Use after route update |
| Metrics | `/recommendations/grafana-check` | `/recommend/grafana-check` | GET | Yes | No after backend route update | Internal/admin only |
| Merchant recommendations | `/recommendations/merchants` | `/recommend/merchants` | GET | Yes | No after backend route update | Use canonical route after update |
| Merchant recommendations | `/recommendations/merchants` | `/recommend/merchants` | POST | Yes | No after backend route update | Use canonical route after update |
| Menu recommendations | `/recommendations/menus` | `/recommend/menus` | GET | Yes | No after backend route update | Use canonical route after update |
| Menu recommendations | `/recommendations/menus` | `/recommend/menus` | POST | Yes | No after backend route update | Use canonical route after update |
| Items | Not implemented | `/recommend/items` | GET | Yes, feature missing | No after implementation | Do not call yet |
| User recommendations | Not implemented | `/recommend/users/{user_id}` | GET | Yes, feature missing | No after implementation | Do not call yet |
| Generate | Not implemented as `/generate` | `/recommend/generate` | POST | Yes, feature missing/route absent | No after implementation | Do not call yet |
| Feedback | Not implemented | `/recommend/feedback` | POST | Yes, feature missing | No after implementation | Do not call yet |

## Public Contract Compliance

Current backend status: **not compliant** with `/recommend/*`.

Reason:

```text
Current: /recommendations/*
Target:  /recommend/*
```

## GCP LB Recommendation

Target mapping:

```text
/recommend/* -> recommendation-backend -> recommendation-service
```

Recommended approach: update the backend to support `/recommend/*` directly.
Then GCP LB does not need URL rewrite.

Temporary fallback, only if an older backend image is deployed:

```text
/recommend/health -> /health
/recommend/grafana-check -> /recommendations/grafana-check
/recommend/merchants -> /recommendations/merchants
/recommend/menus -> /recommendations/menus
```

This rewrite option is less preferred because the public API contract becomes
dependent on URL-map behavior.

## Typo Findings

`recommand` was not found in current deploy files or current recommendation
source file contents. It appears in recommendation branch history:

```text
6348da4 recommand template no api
```

Naming is otherwise mixed between:

```text
module/recommend
/recommendations/*
recommendation-service
ghcr.io/kubereats/recommendation-service:<tag>
```

Recommended standard:

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
