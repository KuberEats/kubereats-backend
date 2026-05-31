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

| Layer         | Responsibility                                  |
| ------------- | ----------------------------------------------- |
| `routes/`   | Receive HTTP requests and return HTTP responses |
| `services/` | Handle recommendation logic                     |
| `repo/`     | Query and mutate PostgreSQL data                |
| `models/`   | Define SQLAlchemy database tables               |
| `schemas/`  | Define Pydantic request and response shapes     |

## Prompt Recommendation Flow

The recommendation module is designed as a replaceable pipeline. The demo
implementation uses SQL and deterministic scoring first, while keeping the
boundaries ready for a future cloud reranker, vector search, or GPU-backed model
service.

```txt
User prompt
  -> POST /merchants
  -> PromptInterpreter
  -> UserContextRetriever
  -> SqlSearchProvider
  -> ConstraintFilter
  -> HeuristicRerankerProvider
  -> TemplateReasonGenerator
  -> Recommendation response
```

Example request:

```json
{
  "userId": 1,
  "campus": "竹科",
  "prompt": "今天想吃清爽一點，不要牛肉，最好是最近沒吃過的，150 以下",
  "limit": 5
}
```

The prompt is converted into three intent buckets:

| Bucket     | Meaning                                         | Example                                      |
| ---------- | ----------------------------------------------- | -------------------------------------------- |
| `must`   | Hard constraints. Results must satisfy these.   | campus, excluded terms, max budget           |
| `avoid`  | Prefer to avoid, but may relax if too few items | recently ordered merchants, repeated choices |
| `prefer` | Soft preferences used for ranking and reasons   | healthy, fast delivery, popular, familiar    |

For the example above, the interpreted intent is conceptually:

```json
{
  "must": {
    "excludedTerms": ["牛肉"],
    "maxBudget": 150
  },
  "avoid": {
    "recentMerchants": true
  },
  "prefer": {
    "terms": ["清爽"],
    "novelty": true
  }
}
```

Pipeline responsibilities:

| Step | Component                     | Responsibility                                                                                            |
| ---- | ----------------------------- | --------------------------------------------------------------------------------------------------------- |
| 1    | `PromptInterpreter`         | Parse the prompt into `must`, `avoid`, and `prefer` intent.                                         |
| 2    | `UserContextRetriever`      | Retrieve recent orders, favorite merchants/categories, user tags, and average spend from PostgreSQL.      |
| 3    | `SqlSearchProvider`         | Find approved candidate merchants or menus with SQL-backed data and keyword matching.                     |
| 4    | `ConstraintFilter`          | Apply hard constraints first, then avoid constraints when enough candidates remain.                       |
| 5    | `HeuristicRerankerProvider` | Score candidates with prompt matches, rating, popularity, budget fit, delivery fit, history, and novelty. |
| 6    | `TemplateReasonGenerator`   | Produce user-facing reasons and machine-readable signals.                                                 |

The history data is contextual: it can add score when the user asks for familiar
food, but it can also subtract score or filter results when the user asks for
something recently not eaten.

Cloud-ready replacement points:

| Local demo component          | Future cloud implementation                                               |
| ----------------------------- | ------------------------------------------------------------------------- |
| `PromptInterpreter`         | LLM interprete to json format                                             |
| `SqlSearchProvider`         | PostgreSQL full-text search, pgvector, Elasticsearch, or Vertex AI Search |
| `HeuristicRerankerProvider` | HTTP reranker service on GKE, Cloud Run GPU, or Vertex AI endpoint        |
| `TemplateReasonGenerator`   | Self-hosted LLM endpoint or managed model endpoint                        |

## Recommendation APIs

Prompt-based endpoints:

```txt
POST /merchants
POST /menus
```

Starter compatibility endpoints:

```txt
GET /merchants?userId=1&campus=竹科&limit=10
GET /menus?userId=1&campus=竹科&merchantId=1&limit=10
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
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=google/gemini-3.1-flash-lite
OPENROUTER_RERANK_MODEL=cohere/rerank-v3.5
```

For running the backend inside Docker Compose:

```env
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/kubereats
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=google/gemini-3.1-flash-lite
OPENROUTER_RERANK_MODEL=cohere/rerank-v3.5
```

`OPENROUTER_API_KEY` enables LLM-based prompt parsing in `PromptInterpreter`.
When the key is missing, or when OpenRouter fails or times out, the backend falls
back to the local deterministic parser. `OPENROUTER_MODEL` is optional and
defaults to `google/gemini-3.1-flash-lite`, a low-latency, low-cost model suited
for converting short food prompts into the `must`, `avoid`, and `prefer` intent
JSON used by the recommendation pipeline.

The same `OPENROUTER_API_KEY` also enables AI reranking in
`HeuristicRerankerProvider`. `OPENROUTER_RERANK_MODEL` is optional and defaults
to `cohere/rerank-v3.5`. The final recommendation score blends the existing
heuristic score with the reranker relevance score:

```txt
normalized_rerank_score = rerank_score / max_rerank_score_in_candidate_batch
final_score = heuristic_score * 0.35 + normalized_rerank_score * 100 * 0.65
```

If reranking is disabled or fails, the backend falls back to the original
heuristic score.

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

| Table                   | Purpose                                   |
| ----------------------- | ----------------------------------------- |
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

When running from the project root, `docker compose up` automatically resets the
dummy data before starting the backend server.

To reset it manually during local backend development, make sure PostgreSQL is
running first:

```sh
docker compose up -d postgres
```

From `kubereats-backend/`, run:

```sh
uv run python create_dummy_data.py
```

Expected output:

```txt
Dummy data reset and created successfully: 14 merchants, 38 menus, 9 staff history orders.
```

The seed data includes 12 approved `竹科` merchants across curry, bento,
healthy meals, noodles, roast meats, Thai, Korean, Italian, sushi, spicy food,
breakfast, and Mexican categories. Use `userId=2` (`staff01`) when testing
recommendations with history: this user has recent repeated orders from bento,
curry, healthy meals, roast meats, noodles, Thai, and Korean merchants. Useful
prompt examples:

```txt
我想要吃咖哩
我想吃清爽一點，不要太油
今天想換口味，最近沒吃過的
我想吃不一樣的，不要最近吃過的
想吃辣一點但不要牛肉
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
