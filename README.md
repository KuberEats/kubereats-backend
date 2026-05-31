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

Canonical routes:

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

`/health` remains available for Kubernetes liveness/readiness probes.

Deprecated compatibility aliases:

```text
GET  /api/finance/history
POST /api/finance/generate-report
```

Do not expose finance routes under `/api/merchant` or `/api/staff`.
