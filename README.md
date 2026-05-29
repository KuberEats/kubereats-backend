# KuberEats Committee Service

福委會審核服務 — 負責審核商家的入駐申請（核准 / 駁回）。

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy
- **Auth**: JWT (PyJWT) — 僅驗證 token，不發 token
- **Config**: pydantic-settings
- **Package Manager**: uv
- **Python**: 3.12

## Project Structure

```
app/
├── main.py                      # FastAPI entry point、health probes
├── database.py                  # SQLAlchemy engine & session
├── core/
│   ├── config.py                # 環境變數集中管理（pydantic-settings）
│   ├── logging.py               # 結構化 JSON logging（GCP Cloud Logging 相容）
│   ├── security.py              # JWT decode（verify only，不發 token）
│   └── dependencies.py          # get_current_user、require_role
├── models/
│   └── kubereats.py             # UserInfo、MerchantInfo
├── schemas/
│   └── committee.py             # MerchantReviewResponse、AuditResultResponse
├── repo/
│   └── committee_repo.py        # Merchant 查詢與狀態更新
├── services/
│   └── committee_service.py     # Approve / reject 邏輯
└── routes/
    └── committee_route.py       # Committee API endpoints
migrations/
└── 001_create_committee_tables.sql  # DB schema（有版本追蹤）
scripts/
└── migrate.py                   # Migration runner（已跑過的自動跳過）
k8s/
└── fuwei-service.yaml           # K8s ConfigMap / Secret / Deployment / Service / NetworkPolicy
```

## API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/committee/merchants/pending` | 列出待審核商家 | committee role |
| GET | `/committee/merchants` | 列出所有商家 | committee role |
| PATCH | `/committee/merchants/{id}/approve` | 核准商家 | committee role |
| PATCH | `/committee/merchants/{id}/reject` | 駁回商家 | committee role |
| GET | `/health/live` | Liveness probe | No |
| GET | `/health/ready` | Readiness probe（含 DB 連線確認） | No |

## Audit Status

| 狀態碼 | 說明 |
|--------|------|
| `0` | 待審核（Pending） |
| `1` | 已核准（Approved） |
| `2` | 已駁回（Rejected） |

只有待審核（`audit_status = 0`）的商家可以被審核，已審核的商家會回傳 400 錯誤。

## Architecture

此服務是 KuberEats 微服務架構的一部分：

```
Frontend (nginx) ─┬→ auth-service        /auth/*
                  ├→ merchant-service    /merchants/*
                  ├→ committee-service   /committee/*   ← 本服務
                  └→ order-service       /orders/*
```

- **JWT**: auth-service 負責發 token，本服務只驗證（共用同一個 `JWT_SECRET_KEY`）
- **DB**: 本服務讀寫 `user_info` 和 `merchant_info` 兩張表

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
uv run python scripts/migrate.py
uv run uvicorn app.main:app --reload
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL 連線字串 | `postgresql://localhost/kubereats` |
| `JWT_SECRET_KEY` | JWT 密鑰（需與 auth-service 一致） | `dev-secret-key` |
| `JWT_ALGORITHM` | JWT 演算法 | `HS256` |

> **注意**：`JWT_SECRET_KEY` 必須與 auth-service 使用相同的值，否則 token 驗證會失敗。

## Testing

```bash
uv sync
uv run pytest tests/ -v
```

測試使用真實 PostgreSQL，需要先確保 `DATABASE_URL` 指向可連線的資料庫。
每個測試結束後透過 transaction rollback 自動還原，不會互相影響。

## Deployment（GCP + Kubernetes）

```bash
# 1. 替換 k8s/fuwei-service.yaml 裡的 image 路徑
#    image: asia-east1-docker.pkg.dev/PROJECT_ID/kubereats/committee-service:latest

# 2. 更新 Secret 裡的 DATABASE_URL 和 JWT_SECRET_KEY

# 3. 套用設定
kubectl apply -f k8s/fuwei-service.yaml
```

## Response Examples

### GET /committee/merchants/pending

```json
[
  {
    "id": 1,
    "userId": 3,
    "merchantName": "好吃便當",
    "campus": "竹科",
    "category": "便當",
    "minOrder": 100,
    "maxOrderQuantity": 50,
    "deliveryTime": "11:30-12:30",
    "tags": ["便當", "台式"],
    "auditStatus": 0,
    "createdAt": "2026-05-14T10:00:00Z",
    "updatedAt": "2026-05-14T10:00:00Z"
  }
]
```

### PATCH /committee/merchants/1/approve

```json
{
  "id": 1,
  "merchantName": "好吃便當",
  "auditStatus": 1,
  "message": "Merchant approved successfully"
}
```
