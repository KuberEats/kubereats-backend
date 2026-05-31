# kubereats-backend

## Public Route Contract

The GCP Load Balancer public prefix for this service is `/tagging`.

Canonical routes:

```text
GET  /tagging/health
GET  /tagging/user/{user_id}
POST /tagging/generate-barcode/{user_id}
```

`/health` remains available for Kubernetes liveness/readiness probes.

Deprecated compatibility aliases:

```text
GET  /api/tagging/user/{user_id}
POST /api/tagging/generate-barcode/{user_id}
```

Early prototype finance-like routes under `/api/merchant/*`, `/api/staff/*`,
and `/api/finance/*` are deprecated/internal only and are not part of the public
LB contract.
