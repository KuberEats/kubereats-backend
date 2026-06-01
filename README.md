# kubereats-backend

## Set up
```bash 
# up back
docker-compose up --build

# off backend
docker-compose down -v
```

## Public Route Contract

The GCP Load Balancer public prefix for this service is `/finance`.

Canonical service-internal routes, assuming the GCP Load Balancer strips the
`/finance` service prefix before forwarding:

```text
GET  /health
GET  /merchant/income-status
GET  /merchant/payouts
GET  /merchant/monthly-total
GET  /merchant/monthly-item-distribution
GET  /staff/expenses
GET  /staff/salary-deductions
GET  /history
POST /generate-report
```

Public LB routes remain:

```text
GET  /finance/health
GET  /finance/merchant/income-status
GET  /finance/merchant/payouts
GET  /finance/merchant/monthly-total
GET  /finance/merchant/monthly-item-distribution
GET  /finance/staff/expenses
GET  /finance/staff/salary-deductions
GET  /finance/history
POST /finance/generate-report
```

The backend also keeps `/finance/*` aliases temporarily for environments that
forward paths without stripping the service prefix. `/health` remains available
for Kubernetes liveness/readiness probes.

Deprecated compatibility aliases:

```text
GET  /api/finance/history
POST /api/finance/generate-report
```

Do not expose finance routes under `/api/merchant` or `/api/staff`.

## Grafana expected
1. status: "ok":
2. database: "connected":
3. today_total_settlement (amount): should **not** be decreased
4. timestamp:
Example:
```json
{"status":"ok","database":"connected","today_total_settlement":0.0,"timestamp":"2026-06-01T08:14:59.829756"}
```