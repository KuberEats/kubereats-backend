# Kubereats Recommendation Backend

FastAPI backend module for KuberEats recommendations.

This branch is initialized as an independent recommendation service. It keeps
`app/models/kubereats.py` aligned with the shared Kubereats database schema,
while the route, service, repository, schema, dummy data, and tests are specific
to the recommendation module.

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
│   ├── repo/
│   └── schemas/
├── create_dummy_data.py
├── Dockerfile.dev
├── pyproject.toml
├── uv.lock
└── README.md
```

## Architecture

```txt
HTTP request
  -> routes
  -> services
  -> repo
  -> models / PostgreSQL
  -> HTTP response
```

Layer responsibilities:

| Layer        | Responsibility                                  |
| ------------ | ----------------------------------------------- |
| `routes/`    | Receive HTTP requests and return HTTP responses |
| `services/`  | Handle recommendation logic                     |
| `repo/`      | Query and mutate PostgreSQL data                |
| `models/`    | Define SQLAlchemy database tables               |
| `schemas/`   | Define Pydantic request and response shapes     |

## Recommendation APIs

Current starter endpoints:

```txt
GET /recommendations/merchants?userId=1&campus=竹科&limit=10
GET /recommendations/menus?userId=1&campus=竹科&merchantId=1&limit=10
```

The starter scorer lives in:

```txt
app/services/recommendation_service.py
```

It ranks approved merchants and menu items with a baseline score using:

- user tags and `history_records`
- merchant name, category, and tags
- merchant rating and order count

This is intentionally simple so it can be replaced later by collaborative
filtering, vector search, a feature store, or another recommendation strategy
without changing the route/repository boundaries.

## Requirements

- Python 3.12+
- Docker
- `uv`

Install dependencies:

```sh
uv sync
```

## Environment Variables

Create a `.env` file in `kubereats-backend/`.

For running the backend locally on your machine:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/kubereats
```

For running the backend inside Docker Compose:

```env
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/kubereats
```

## Run Locally

Start PostgreSQL from the project root:

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

## Run Test

From the project root:

```sh
docker compose down -v
docker compose up -d postgres backend
```

From this backend directory:

```sh
npm test
```

`npm test` runs Vitest and uses `test/global-setup.ts` to reset dummy data before
the API tests.

## Database Models

The shared SQLAlchemy models are defined in:

```txt
app/models/kubereats.py
```

Current tables:

| Table                 | Purpose                                   |
| --------------------- | ----------------------------------------- |
| `merchant_info`       | Merchant profile and audit status         |
| `menu`                | Menu items sold by merchants              |
| `menu_daily_capacity` | Per-menu daily max and remaining quantity |
| `user_info`           | Users, staff, admins, and merchants       |
| `tags`                | User preference tags                      |
| `user_tags`           | User/tag association table                |
| `orders`              | User orders                               |
| `order_items`         | Menu items included in each order         |
| `finance`             | Merchant settlement and order finance     |

Do not diverge `app/models/kubereats.py` from the shared backend schema unless
the team changes the shared schema intentionally.

During development, tables are created automatically in `app/main.py`:

```python
Base.metadata.create_all(bind=engine)
```

For production or team development, this should later be replaced with Alembic
migrations.

## Create Dummy Data

Make sure PostgreSQL is running first:

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

## Useful Commands

Format and lint:

```sh
uv run ruff check .
```

Run Python tests:

```sh
uv run pytest
```

Run API tests:

```sh
npm test
```
