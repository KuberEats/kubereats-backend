# Kubereats Backend

FastAPI backend for KuberEats.

The backend uses:

- FastAPI for the HTTP API
- SQLAlchemy for PostgreSQL models and database access
- PostgreSQL as the database
- `uv` for Python dependency and virtual environment management

## Project Structure

```txt
kubereats-backend/
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models/
│   │   └── kubereats.py
│   ├── routes/
│   ├── services/
│   ├── repositories/
│   └── schemas/
├── create_dummy_data.py
├── Dockerfile.dev
├── pyproject.toml
├── uv.lock
└── README.md
```

## Architecture

The backend should follow a layered structure:

```txt
HTTP request
  -> routes
  -> services
  -> repositories
  -> models / PostgreSQL
  -> HTTP response
```

Layer responsibilities:

Route = API 門口
Service = 商業邏輯
Repository = 資料庫操作
Schema = request / response 格式
Model = database table

| Layer             | Responsibility                                  |
| ----------------- | ----------------------------------------------- |
| `routes/`       | Receive HTTP requests and return HTTP responses |
| `services/`     | Handle business logic                           |
| `repositories/` | Query and mutate PostgreSQL data                |
| `models/`       | Define SQLAlchemy database tables               |
| `schemas/`      | Define Pydantic request and response shapes     |

## Requirements

- Python 3.12+
- Docker
- `uv`

Install `uv` if needed:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Check installation:

```sh
uv --version
```

## Environment Variables

Create a `.env` file in `kubereats-backend/`.

For running the backend locally on your machine:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/kubereats
QUEUE_BACKEND=fake
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
DISPATCH_LEAD_MINUTES=30
MAX_SCHEDULE_DAYS=30

GCP_PROJECT_ID=
GCP_LOCATION=
GCP_CLOUD_TASKS_QUEUE=
GCP_TASK_HANDLER_URL=
GCP_TASK_SERVICE_ACCOUNT_EMAIL=
```

For running the backend inside Docker Compose:

```env
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/kubereats
```

The difference is the database host:

- `localhost`: local backend process connects to PostgreSQL exposed on your machine
- `postgres`: Docker backend container connects to the Docker Compose `postgres` service

## Install Dependencies

From `kubereats-backend/`:

```sh
uv sync
```

Add a runtime dependency:

```sh
uv add package-name
```

Add a development dependency:

```sh
uv add --dev package-name
```

## Run Locally

Start PostgreSQL from `kubereats-backend/`:

```sh
docker compose up -d postgres
```

Then start the backend from `kubereats-backend/`:

```sh
uv run uvicorn app.main:app --reload
```

Open:

```txt
http://localhost:8000/docs
```

Health check:

```txt
http://localhost:8000/health
```

## Run with Docker Compose

From `kubereats-backend/`:

```sh
docker compose up --build
```

This starts:

- backend on http://localhost:8000
- PostgreSQL on localhost:5432
- RabbitMQ management UI on http://localhost:15672

  ```bash
  docker compose down -v # this will reset db data too
  docker compose up -d postgres rabbitmq backend
  ```

## Run Test

in root:

```bash
docker compose down -v
docker compose up -d postgres rabbitmq backend
```

in backend/ :

```
npm test # which will run docker compose exec -T backend uv run python create_dummy_data.py

```

npm test
→ vitest run
→ 讀 vitest.config.ts
→ 發現 globalSetup
→ 執行 test/global-setup.ts
→ docker compose exec backend uv run python create_dummy_data.py
→ 開始跑 *.test.ts

## Database Models

The current SQLAlchemy models are defined in:

```txt
app/models/kubereats.py
```

Current tables:

| Table                   | Purpose                                    |
| ----------------------- | ------------------------------------------ |
| `merchant_info`       | Merchant profile and audit status          |
| `menu`                | Menu items sold by merchants               |
| `menu_daily_capacity` | Per-menu daily max and remaining quantity  |
| `user_info`           | Users, staff, admins, and merchants        |
| `orders`              | User orders                                |
| `order_items`         | Menu items included in each order          |
| `finance`             | Merchant settlement and order finance data |
| `outbox_events`       | Transactional outbox for delayed work      |

During development, tables are created automatically in `app/main.py`:

```python
Base.metadata.create_all(bind=engine)
```

For production or team development, this should later be replaced with Alembic migrations. The order scheduler SQL migration is available at `migrations/20260527_order_scheduler.sql`.

## Order Scheduling

The existing order flow remains synchronously confirmed. `POST /orders` still validates the user, merchant, menu, minimum order, and per-day menu capacity in one database transaction. A successful response means the order exists and capacity for its service date has already been deducted.

Scheduled orders add future pickup/service timing; they do not move stock confirmation into a worker. The queue is only for later release/dispatch work, notifications, and reconciliation.

New order fields:

| Field | Purpose |
| --- | --- |
| `order_number` | External unique order number, generated from service date and DB id |
| `scheduled_for` | Optional user pickup/service datetime |
| `dispatch_at` | Time at which release work becomes available |
| `schedule_status` | `not_scheduled`, `scheduled`, `released`, `failed`, or `cancelled` |
| `idempotency_key` | Optional request idempotency key, unique per user when present |
| `released_at`, `cancelled_at`, `cancellation_reason` | Scheduler lifecycle audit fields |

`order_status` keeps the business order lifecycle (`0` in progress, `1` complete, `2` cancelled). `schedule_status` tracks only delayed release lifecycle.

### API Changes

Create an immediate order:

```http
POST /orders
```

Create a scheduled order:

```json
{
  "userId": 1,
  "scheduledFor": "2026-05-28T12:00:00+08:00",
  "items": [{ "menuId": 1, "quantity": 1 }]
}
```

`Idempotency-Key` is supported on `POST /orders`. Reusing the same key and same payload returns the original order. Reusing the same key with a different payload returns `409 Conflict`.

Cancel an unreleased scheduled order:

```http
POST /orders/{id}/cancel
```

Internal task endpoint:

```http
POST /internal/tasks/orders/release
```

The task handler is idempotent. If the order was already released or cancelled, it returns success without repeating side effects.

### Transactional Outbox

Scheduled order creation writes the order, order items, capacity deduction, finance rows, and `order.release_requested` outbox event in the same transaction. The dispatcher later scans unpublished due events and enqueues tasks. This avoids the failure mode where an order commit succeeds but direct enqueue fails and the release task is lost.

Run one dispatcher pass:

```sh
uv run python -m app.commands.dispatch_outbox
```

The dispatcher is safe to rerun. On success it sets `published_at`; on failure it increments `retry_count` and preserves the event for retry.

### Queue Backends

Set `QUEUE_BACKEND`:

| Backend | Use |
| --- | --- |
| `fake` | Unit tests and local development without external queue |
| `rabbitmq` | Local Docker Compose queue; messages are published to `order.release` |
| `cloud_tasks` | GCP delayed delivery to the internal HTTP task handler |

Business services depend only on the `TaskQueue` protocol. RabbitMQ and Cloud Tasks code lives under `app/queues/`.
For local RabbitMQ delivery, `app.commands.consume_order_release` consumes `order.release` and POSTs the payload to the internal task handler.

### Sequence

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant DB
    participant Dispatcher
    participant Queue
    participant Handler

    Client->>API: POST /orders scheduledFor
    API->>DB: validate + deduct menu_daily_capacity
    API->>DB: insert order, items, finance, outbox
    DB-->>API: commit
    API-->>Client: 201 Created
    Dispatcher->>DB: scan due outbox events
    Dispatcher->>Queue: enqueue order release
    Dispatcher->>DB: mark published_at
    Queue->>Handler: POST /internal/tasks/orders/release
    Handler->>DB: lock order
    Handler->>DB: scheduled -> released + order.released outbox
    Handler-->>Queue: 2xx
```

### Local Scheduling Development

```sh
cp .env.example .env
docker compose up -d postgres rabbitmq backend
uv run python create_dummy_data.py
QUEUE_BACKEND=rabbitmq uv run python -m app.commands.dispatch_outbox
QUEUE_BACKEND=rabbitmq uv run python -m app.commands.consume_order_release
```

RabbitMQ UI:

```txt
http://localhost:15672
```

### Schema Migration

This repository currently creates tables with `Base.metadata.create_all`; it does not use Alembic. The scheduler schema is represented in SQLAlchemy models and as a manual SQL migration at:

```txt
migrations/20260527_order_scheduler.sql
```

For a fresh local database, `create_dummy_data.py` drops and recreates the schema. For an existing PostgreSQL database, apply the SQL migration before deploying this code.

### GCP Deployment Notes

Recommended mapping:

| Need | GCP service |
| --- | --- |
| API and internal task handler | Cloud Run or GKE |
| Delayed order release task | Cloud Tasks |
| Recurring outbox recovery/reconciliation | Cloud Scheduler |
| Event fan-out for notifications | Pub/Sub |

Cloud Tasks uses at-least-once delivery. The internal release handler must remain idempotent and must not send notifications directly inside the DB transaction. Notification work should consume `order.released` or another queue/event.

Cloud Tasks supports scheduling up to 30 days in the future. This implementation defaults `MAX_SCHEDULE_DAYS=30`. To support longer reservations later, keep long-horizon work in PostgreSQL and use Cloud Scheduler to create near-term Cloud Tasks.

Required Cloud Tasks environment:

```env
QUEUE_BACKEND=cloud_tasks
GCP_PROJECT_ID=your-project
GCP_LOCATION=asia-east1
GCP_CLOUD_TASKS_QUEUE=order-release
GCP_TASK_HANDLER_URL=https://your-internal-url/internal/tasks/orders/release
GCP_TASK_SERVICE_ACCOUNT_EMAIL=cloud-tasks-invoker@your-project.iam.gserviceaccount.com
```

No credentials or cloud resource names are hard-coded in the application.

## Create Dummy Data

Make sure PostgreSQL is running first from `kubereats-backend/`:

```sh
docker compose up -d postgres
```

From `kubereats-backend/`, run:

```sh
uv run python create_dummy_data.py
```

Expected output:

```txt
Dummy data reset and created successfully.
```

The script clears existing dummy tables, resets ids, and creates fresh sample data again.

To run the same script inside Docker, start PostgreSQL and the backend from `kubereats-backend/`:

```sh
docker compose up -d postgres backend
```

Then run:

```sh
docker compose exec backend uv run python create_dummy_data.py
```

## Inspect PostgreSQL Data

From `kubereats-backend/`:

```sh
docker compose exec postgres psql -U postgres -d kubereats
```

Show tables:

```sql
\dt
```

Query data:

```sql
SELECT * FROM merchant_info;
SELECT * FROM menu;
SELECT * FROM menu_daily_capacity;
SELECT * FROM user_info;
SELECT * FROM orders;
SELECT * FROM finance;
```

Exit:

```sql
\q
```

## Useful Commands

Format and lint:

```sh
uv run ruff check .
```

Run tests:

```sh
uv run pytest
```

Check installed packages:

```sh
uv pip list
```

## Version Control

This backend is managed as its own Git repository.

Common workflow:

```sh
git status
git add .
git commit -m "Describe your change"
```
