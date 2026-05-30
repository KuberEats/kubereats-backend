# KuberEats Verification Service

Verification/Auth 服務 — 負責使用者註冊、登入、JWT token 發放與刷新。此服務是 KuberEats backend 第一個 Kubernetes deployment baseline，其他 backend microservices 可以參考 `deploy/k8s/` 結構。

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy
- **Auth**: JWT (PyJWT) + bcrypt
- **Config**: pydantic-settings
- **Package Manager**: uv
- **Python**: 3.12

## Project Structure

```
app/
├── main.py                  # FastAPI entry point, probes, metrics
├── database.py              # SQLAlchemy engine & session
├── core/
│   ├── config.py            # 環境變數集中管理（pydantic-settings）
│   ├── logging.py           # 結構化 JSON logging（GCP Cloud Logging 相容）
│   ├── security.py          # JWT sign/verify、bcrypt hash/verify
│   └── dependencies.py      # get_current_user、require_role
├── models/
│   └── kubereats.py         # UserInfo、RefreshToken
├── schemas/
│   └── auth.py              # Request / Response schemas
├── repo/
│   └── user_repo.py         # User & token CRUD
├── services/
│   └── auth_service.py      # Register、login、refresh 邏輯
└── routes/
    └── auth_route.py        # Auth API endpoints
migrations/
└── 001_create_auth_tables.sql  # DB schema（有版本追蹤）
scripts/
└── migrate.py               # Migration runner（已跑過的自動跳過）
deploy/k8s/                  # Kustomize manifests（dev/prod overlays）
```

## API Endpoints

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| POST | `/auth/register` | 註冊新使用者 | No |
| POST | `/auth/login` | 登入，取得 JWT token | No |
| POST | `/auth/refresh` | 刷新 access token | No |
| GET | `/auth/me` | 取得目前使用者資訊 | Yes |
| GET | `/health/live` | Liveness probe | No |
| GET | `/healthz` | Liveness probe（K8s 慣例） | No |
| GET | `/health/ready` | Readiness probe（含 DB 連線確認） | No |
| GET | `/readyz` | Readiness probe（K8s 慣例） | No |
| GET | `/metrics` | Prometheus text metrics | No |

## User Roles

| 角色 | 說明 |
|------|------|
| `employee` | 一般員工（訂餐） |
| `merchant` | 商家（管理菜單） |
| `committee` | 福委會（審核商家） |

## Architecture

此服務是 KuberEats 微服務架構的一部分：

```
Frontend (nginx) ─┬→ verification-service  /auth/*              ← 本服務
                  ├→ merchant-service    /merchants/*
                  ├→ committee-service   /committee/*
                  └→ order-service       /orders/*
```

- **JWT**: 本服務負責發 token，其他服務使用同一個 `JWT_SECRET_KEY` 驗證 token
- **DB**: 本服務管理 `user_info` 和 `refresh_tokens` 兩張表

## Auth Flow

```
Register: POST /auth/register {username, password, role}
    → validate role → check duplicate → bcrypt hash → save → return user

Login: POST /auth/login {username, password}
    → verify password → issue access_token (30min) + refresh_token (7d)

Protected API: Authorization: Bearer <access_token>
    → decode JWT → inject current_user

Token Refresh: POST /auth/refresh {refreshToken}
    → validate token → issue new pair → revoke old refresh_token (rotation)
```

## Local Development

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [uv](https://docs.astral.sh/uv/)

### 1. 設定環境變數

```bash
cp .env.example .env
# 視需要修改 .env 內容
```

### 2. 用 Docker Compose 啟動（建議）

```bash
docker compose up --build
```

啟動時會自動執行 `scripts/migrate.py` 建立 DB schema，再啟動 API server。

- API：http://localhost:8000
- API Docs：http://localhost:8000/docs

### 3. 直接在本機執行

```bash
uv sync
uv run python scripts/migrate.py   # 建立 DB schema
uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --reload
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Runtime environment | `local` |
| `LOG_LEVEL` | Uvicorn log level | `info` |
| `PORT` | HTTP listen port | `8000` |
| `DATABASE_URL` | PostgreSQL 連線字串 | `postgresql://localhost/kubereats` |
| `DB_POOL_SIZE` | SQLAlchemy pool size per process | `5` |
| `DB_MAX_OVERFLOW` | Extra DB connections per process | `10` |
| `DB_POOL_TIMEOUT` | Pool wait timeout seconds | `30` |
| `AUTO_CREATE_TABLES` | Startup `create_all` behavior | `true` |
| `JWT_SECRET_KEY` | JWT 密鑰（所有服務須一致） | `dev-secret-key` |
| `JWT_ALGORITHM` | JWT 演算法 | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token 過期時間（分鐘） | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token 過期時間（天） | `7` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` | Future SMTP settings | placeholders only |
| `MAILGUN_API_KEY`, `MAILGUN_DOMAIN` | Future Mailgun settings | placeholders only |

Copy `.env.example` for local development and fill in local values. Do not commit real secrets.

> **注意**：`JWT_SECRET_KEY` 的 default 值僅供本地開發使用，部署前務必替換。

### Database & Migrations

此服務使用 SQLAlchemy 搭配 PostgreSQL，並透過 `scripts/migrate.py` 執行有版本追蹤的 SQL migration。當 `AUTO_CREATE_TABLES=true` 時，啟動時也會呼叫 `Base.metadata.create_all()`。Kubernetes 部署時，`DATABASE_URL` 必須指向外部 PostgreSQL 穩定 endpoint（如 Patroni/HAProxy/VIP/DNS）。此 repo 不包含 PostgreSQL 部署。

## Testing

```bash
uv sync
uv run pytest tests/ -v
```

測試使用真實 PostgreSQL（auth 測試）或 in-memory SQLite（health 測試）。  
Auth 測試每個 case 結束後透過 transaction rollback 自動還原，不會互相影響。

## Docker

```bash
docker build -t ghcr.io/kubereats/kubereats-verification:dev .
docker run --rm -p 8000:8000 --env-file .env ghcr.io/kubereats/kubereats-verification:dev
```

容器會執行 `scripts/migrate.py`，再以 `uvicorn app.main:app` 監聽 `PORT`，log 輸出至 stdout/stderr。

## Kubernetes

Kubernetes manifests 位於 `deploy/k8s/`，使用 kustomize：

```bash
kubectl -n kubereats-dev create secret generic verification-secret \
  --from-literal=DATABASE_URL='postgresql+psycopg2://user:password@postgres.example.internal:5432/kubereats' \
  --from-literal=JWT_SECRET_KEY='replace-with-real-shared-secret'

kubectl apply -k deploy/k8s/overlays/dev
kubectl -n kubereats-dev rollout status deploy/verification
```

詳見 `deploy/k8s/README.md` 的部署、smoke test、rollback 與 troubleshooting 步驟。

## Response Examples

### POST /auth/login

```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIs...",
  "refreshToken": "eyJhbGciOiJIUzI1NiIs...",
  "tokenType": "bearer"
}
```

### GET /auth/me

```json
{
  "id": 1,
  "username": "john",
  "email": null,
  "role": "employee",
  "isActive": true,
  "createdAt": "2026-05-14T10:00:00Z",
  "updatedAt": "2026-05-14T10:00:00Z"
}
```
