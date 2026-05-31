# kubereats-backend

## Public Route Contract

The GCP Load Balancer public prefix for this service is `/tagging`.

Canonical service-internal routes, assuming the GCP Load Balancer strips the
`/tagging` service prefix before forwarding:

```text
GET  /health
GET  /user/{user_id}
POST /generate-barcode/{user_id}
```

Public LB routes remain:

```text
GET  /tagging/health
GET  /tagging/user/{user_id}
POST /tagging/generate-barcode/{user_id}
```

The backend also keeps `/tagging/*` aliases temporarily for environments that
forward paths without stripping the service prefix. `/health` remains available
for Kubernetes liveness/readiness probes.

Deprecated compatibility aliases:

```text
GET  /api/tagging/user/{user_id}
POST /api/tagging/generate-barcode/{user_id}
```

Early prototype finance-like routes under `/api/merchant/*`, `/api/staff/*`,
and `/api/finance/*` are deprecated/internal only and are not part of the public
LB contract.
