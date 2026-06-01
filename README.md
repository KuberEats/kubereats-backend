# KuberEats Order Consumer

`order-consumer` is the internal worker that completes reservation-based orders.
It does not expose a public API. The public flow starts in
`order-scheduler-service`, which accepts reservation requests and writes
`reservation_requests`. This worker polls pending reservations, reserves menu
capacity, and creates the final order records.

## Runtime Flow

1. `order-scheduler-service` receives `POST /order-scheduler/reservation-requests`.
2. The API validates the user, merchant, menu items, service date, and
   idempotency key.
3. The API creates a `PENDING_RESERVATION` row and reservation items.
4. `order-consumer-service` polls pending reservations from PostgreSQL.
5. The worker claims rows with a lease and row locks.
6. For each reservation, the worker atomically:
   - reserves capacity in `reservation_capacity_slots`
   - creates `orders`
   - creates `order_items`
   - creates `finance`
   - marks the reservation as `RESERVED`
7. If capacity is unavailable, the worker marks the reservation as `SOLD_OUT`.

The capacity update and order creation happen in the same DB transaction so the
system does not leave a reservation as reserved without an order.

## Local Development

Install dependencies:

```bash
uv sync --dev
```

Run one polling cycle:

```bash
DATABASE_URL='postgresql://<db-user>:<db-password>@<db-host>:5432/kubereats' \
  uv run python -m app.commands.process_reservations --poll --limit 10
```

Run the long-lived worker:

```bash
DATABASE_URL='postgresql://<db-user>:<db-password>@<db-host>:5432/kubereats' \
  uv run python -m app.commands.run_order_consumer
```

Do not commit real `DATABASE_URL`, DB passwords, or service tokens.

## Tests

Run the Python tests:

```bash
uv run pytest tests/ -q
```

Build and test with Docker:

```bash
docker build -f Dockerfile.dev -t kubereats-order-consumer:local .
docker run --rm \
  -e DATABASE_URL=sqlite+pysqlite:///:memory: \
  kubereats-order-consumer:local \
  uv run pytest tests/ -q
```

## Configuration

Important environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | required | PostgreSQL connection URL from Kubernetes Secret `kubereats-db-app`. |
| `RESERVATION_DB_POLLING_BATCH_SIZE` | `25` | Max reservations claimed per poll. |
| `RESERVATION_PROCESSING_LEASE_SECONDS` | `300` | Lease duration while a reservation is being processed. |
| `ORDER_CONSUMER_POLL_INTERVAL_SECONDS` | `2` | Delay between polling cycles. |
| `ORDER_CONSUMER_METRICS_ADDRESS` | `0.0.0.0` | Metrics bind address. |
| `ORDER_CONSUMER_METRICS_PORT` | `9100` | Metrics port. |

## Kubernetes

Dev manifests live under:

```text
deploy/k8s/base/order-consumer-service
deploy/k8s/overlays/dev/order-consumer-service
```

The worker deployment is internal only:

- no public Ingress
- no LoadBalancer
- no business HTTP API
- `ClusterIP` service only for Prometheus metrics on port `9100`

Render the dev overlay:

```bash
docker run --rm -v "$PWD":/work -w /work \
  registry.k8s.io/kustomize/kustomize:v5.4.2 \
  build deploy/k8s/overlays/dev/order-consumer-service
```

Check the deployed worker:

```bash
kubectl -n kubereats-dev get deploy,svc,pod \
  -l app.kubernetes.io/name=order-consumer-service
```

Check logs:

```bash
kubectl -n kubereats-dev logs deploy/order-consumer-service --tail=120
```

## Metrics And Alerts

The worker exposes Prometheus metrics at:

```text
http://order-consumer-service.kubereats-dev.svc.cluster.local:9100/metrics
```

Current metrics include:

- `order_consumer_up`
- `order_consumer_poll_total`
- `order_consumer_reservation_processed_total`
- `order_consumer_reservation_failed_total`
- `order_consumer_last_poll_timestamp_seconds`

The base manifests include:

- `ServiceMonitor` for Prometheus scraping
- `PrometheusRule` for target down, no available pods, and reservation failures
- `NetworkPolicy` to restrict ingress to metrics and egress to DNS/PostgreSQL

## Operational Notes

- Do not run this worker against production DB with local credentials.
- Do not use the app DB user for manual DBA work.
- Do not manually edit production orders unless there is an approved emergency
  ticket, reviewed SQL, backup, verification, and rollback plan.
- Test data should be created through seed scripts, backend APIs, or admin UI.
