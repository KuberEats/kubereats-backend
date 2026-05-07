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

## Run with Docker Compose

From the project root:

```sh
docker compose up --build
```

This starts:

- frontend on http://localhost:5173
- backend on http://localhost:8000
- PostgreSQL on localhost:5432

## Database Models

The current SQLAlchemy models are defined in:

```txt
app/models/kubereats.py
```

Current tables:

| Table             | Purpose                                    |
| ----------------- | ------------------------------------------ |
| `merchant_info` | Merchant profile and audit status          |
| `menu`          | Menu items sold by merchants               |
| `menu_daily_capacity` | Per-menu daily max and remaining quantity |
| `user_info`     | Users, staff, admins, and merchants        |
| `orders`        | User orders                                |
| `order_items`   | Menu items included in each order          |
| `finance`       | Merchant settlement and order finance data |

During development, tables are created automatically in `app/main.py`:

```python
Base.metadata.create_all(bind=engine)
```

For production or team development, this should later be replaced with Alembic migrations.

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

The script clears existing dummy tables, resets ids, and creates fresh sample data again.

To run the same script inside Docker, start PostgreSQL and the backend from the project root:

```sh
docker compose up -d postgres backend
```

Then run:

```sh
docker compose exec backend python create_dummy_data.py
```

## Inspect PostgreSQL Data

From the project root:

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
