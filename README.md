# KuberEats Notification Service

Internal email notification microservice for KuberEats. It accepts authenticated
service-to-service requests, validates the fixed template and payload, stores an
idempotent notification request, queues a background job, and sends email through
an email provider adapter.

## Architecture

Flow:

1. Internal service calls `POST /internal/v1/notifications/email`.
2. API validates bearer token, template permission, recipient type, payload schema,
   idempotency key, and correlation id.
3. API stores `notification_requests` and queues only `{notificationId, correlationId}`.
4. Worker loads the request from DB, renders fixed subject/html/text templates, calls
   the configured provider, and records `notification_delivery_attempts`.
5. Status moves through `QUEUED`, `PROCESSING`, `SENT`, `RETRYING`, `FAILED`, or
   `DEAD_LETTER`.

API and worker are separate processes for independent Kubernetes scaling.

## API Example

```bash
curl -i http://localhost:8000/internal/v1/notifications/email \
  -H 'Authorization: Bearer dev-order-token' \
  -H 'Idempotency-Key: order-ORD-20260601-0001-confirmed' \
  -H 'X-Correlation-Id: corr-001' \
  -H 'Content-Type: application/json' \
  -d '{
    "templateKey": "employee.order.confirmed",
    "recipient": {
      "type": "EMPLOYEE",
      "id": "EMP001",
      "email": "employee@example.com",
      "name": "王小明"
    },
    "locale": "zh-TW",
    "payload": {
      "orderId": "ORD-20260601-0001",
      "vendorName": "健康便當",
      "pickupDate": "2026-06-03",
      "pickupTime": "12:00-12:30",
      "pickupLocation": "A 廠一樓領餐區",
      "amount": 120,
      "detailUrl": "https://food.example.com/orders/ORD-20260601-0001"
    }
  }'
```

Query status:

```bash
curl http://localhost:8000/internal/v1/notifications/{notificationId} \
  -H 'Authorization: Bearer dev-order-token'
```

## Template Keys

| Key | Caller | Recipient |
| --- | --- | --- |
| `employee.order.confirmed` | `order-service` | `EMPLOYEE` |
| `employee.order.failed` | `order-service` | `EMPLOYEE` |
| `employee.order.cancelled` | `order-service` | `EMPLOYEE` |
| `committee.settlement.review_required` | `finance-service` | `COMMITTEE` |
| `committee.vendor.approval_required` | `merchant-service` | `COMMITTEE` |
| `committee.menu.review_required` | `merchant-service` | `COMMITTEE` |
| `vendor.settlement.confirmed` | `finance-service` | `VENDOR` |
| `vendor.approval.result` | `committee-service` | `VENDOR` |
| `vendor.menu.change_result` | `committee-service` | `VENDOR` |

Request bodies cannot provide custom subject or HTML body.

## Environment Variables

| Variable | Description |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy DB URL. PostgreSQL is expected in containers. |
| `REDIS_URL` | Celery broker/backend URL. |
| `INTERNAL_SERVICE_TOKENS` | Comma-separated `service:token` pairs. |
| `EMAIL_PROVIDER` | `local`, `production`, or `memory`. |
| `SMTP_HOST` | Local SMTP host for MailHog. |
| `SMTP_PORT` | Local SMTP port. |
| `SMTP_FROM_EMAIL` | Email sender address. |
| `MAX_DELIVERY_ATTEMPTS` | Reserved for provider-specific worker tuning. |
| `RATE_LIMIT_PER_MINUTE` | Process-local MVP request limit per source service. |

## Local Development

SQLite is supported for local development and fast API tests because it requires
no external database process. The application code still uses SQLAlchemy models
and repositories; application services do not contain SQLite-specific SQL.

Create local environment:

```bash
cp .env.example .env
uv sync
uv run python scripts/migrate.py
uv run uvicorn app.main:app --reload
```

For local SQLite, keep:

```env
DATABASE_URL=sqlite:///./notification.db
EMAIL_PROVIDER=memory
```

Clear and rebuild the local SQLite database:

```bash
rm -f notification.db
uv run python scripts/migrate.py
```

Run the worker locally when Redis and SMTP are available:

```bash
uv run celery -A app.worker.celery_app worker --loglevel=info
```

Docker Compose starts PostgreSQL, Redis, MailHog, API, and worker:

```bash
docker compose up --build
```

Open MailHog at <http://localhost:8025>.

## Migration Strategy

The service uses SQLAlchemy as the database abstraction. `idempotency_key` has a
database-level unique constraint and `payload_hash` is persisted to detect the
same idempotency key with different request content.

Migration command:

```bash
uv run python scripts/migrate.py
```

SQLite migration uses SQLAlchemy metadata to build the local schema. PostgreSQL
migration executes `migrations/001_create_notification_tables.sql`, including
PostgreSQL `JSONB` for `payload`. Repository and application behavior stay the
same across both environments.

SQLite is only for local development and fast tests. Production should not use
SQLite. Production DB should follow the platform database choice; based on the
existing services in this repository, PostgreSQL is the expected production-like
database. Before release, integration tests must pass against PostgreSQL.

## Local End-to-End Test

1. Start DB, Redis, MailHog, API, and worker with `docker compose up --build`.
2. Send the curl request above.
3. Open <http://localhost:8025> and confirm the email exists.
4. Query the returned notification id and confirm `status` becomes `SENT`.

## Tests

```bash
uv run pytest
uv run ruff check .
uv run python -m compileall app tests scripts
```

Fast tests use SQLite and in-memory fakes where possible:

```bash
DATABASE_URL=sqlite:///./notification_test.db uv run python scripts/migrate.py
DATABASE_URL=sqlite:///./notification_test.db uv run pytest \
  tests/test_templates.py \
  tests/test_notification_service.py \
  tests/test_retry_policy.py \
  tests/test_api.py
```

Live API integration tests require a running API and PostgreSQL:

```bash
LIVE_API_BASE_URL=http://127.0.0.1:8000 \
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/kubereats_notification \
uv run pytest tests/integration/test_live_api.py
```

Worker + MailHog E2E tests require API, worker, PostgreSQL, Redis, and MailHog:

```bash
LIVE_API_BASE_URL=http://127.0.0.1:8000 \
MAILHOG_API_URL=http://127.0.0.1:8025 \
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/kubereats_notification \
uv run pytest tests/integration/test_worker_mailhog_e2e.py
```

## CI Integration Test

GitHub Actions workflow: `.github/workflows/notification-service-ci.yml`.

Triggers:

- Pull requests
- Pushes to `main`
- Pushes to `develop`
- Pushes to `module/**`, including `module/notification`

Jobs:

- `lint-typecheck-unit-sqlite`: installs Python 3.12 and dependencies with uv,
  runs SQLite migration, ruff lint, `compileall` as the current typecheck
  substitute, unit tests, and fast SQLite API tests. This validates template
  registry, payload validation, authorization policy, idempotency logic, status
  query authorization, retry policy, and DB unique constraint behavior.
- `postgres-api-integration`: starts temporary PostgreSQL and Redis service
  containers, runs PostgreSQL migration, starts the notification API process,
  waits for `/health/ready`, then runs live API integration tests. This validates
  API connectivity to PostgreSQL, migration execution, POST/GET behavior, 401,
  403, duplicate idempotency, conflict idempotency, and the DB unique constraint.
- `worker-mailhog-e2e`: starts temporary PostgreSQL, Redis, and MailHog service
  containers, starts notification API and worker processes, sends an
  `employee.order.confirmed` request, verifies MailHog received exactly one
  email, and confirms notification status reaches `SENT`.

The CI services are one-time test environments inside GitHub Actions. They are
not deployments and do not create long-lived infrastructure.

## Retry And Failure Handling

Transient provider failures are retried after 1 minute, 5 minutes, and 30 minutes.
After the third failed attempt, the worker moves the notification to `DEAD_LETTER`.
Permanent provider failures move the notification to `FAILED`.

Email failure never rolls back the caller service business transaction.

## Adding A Template

1. Add a strict pydantic payload model in `app/templates/registry.py`.
2. Add an `EmailTemplate` entry with key, version, allowed source services,
   recipient types, subject, HTML, and text templates.
3. Add unit tests for registry lookup, authorization, validation, and HTML escaping.
4. Document the key in this README.

## Future Extensions

The service can add in-app notifications, push notifications, SMS, provider-specific
adapters such as AWS SES or Mailgun, queue-depth based worker autoscaling, and
ServiceMonitor resources for Prometheus Operator.
