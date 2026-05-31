# GCP LB Path Routing Plan

The public API domain already carries the API namespace:

```text
api.kubereats.click
```

Do not add another `/api` path segment for service routing. Public paths must
use:

```text
api.kubereats.click/<service-name>/*
```

## Phase 2a Routes

```text
/finance/* -> finance-backend -> finance-service
/tagging/* -> tagging-backend -> tagging-service
```

Public health checks:

```text
GET https://api.kubereats.click/finance/health
GET https://api.kubereats.click/tagging/health
```

Kubernetes probes remain service-internal:

```text
GET /health
```

## Rewrite Policy

No GCP URL rewrite is required for Phase 2a finance/tagging after the updated
service images are deployed. The applications expose `/finance/*` and
`/tagging/*` directly.

Temporary fallback only, for older images:

```text
/finance/* rewrite to /api/finance/*
/tagging/* rewrite to /api/tagging/*
```

Remove temporary rewrites after deploying the route-contract fixed images.

## Deprecated Paths

These are compatibility aliases only and must not be used in the public LB URL
map:

```text
/api/finance/*
/api/tagging/*
```

The tagging service also has early prototype finance-like routes under
`/api/merchant/*`, `/api/staff/*`, and `/api/finance/*`. Treat them as
deprecated/internal, not public routes.
