# KuberEats Merchant Service

商家服務 — 負責前台商家查詢、商家入駐申請、商家資訊管理、菜單 CRUD、今日訂單彙整與確認。

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
│   └── kubereats.py             # UserInfo、MerchantInfo、Menu、Order、OrderItem
├── schemas/
│   └── merchant.py              # Merchant、Menu、OrderSummary schemas
├── repo/
│   └── merchant_repo.py         # Merchant、Menu CRUD 與訂單查詢
├── services/
│   └── merchant_service.py      # Apply、Menu CRUD、訂單彙整邏輯
└── routes/
    └── merchant_route.py        # Merchant API endpoints
migrations/
└── 001_create_merchant_tables.sql  # DB schema（有版本追蹤）
scripts/
└── migrate.py                   # Migration runner（已跑過的自動跳過）
k8s/
└── merchant-service.yaml        # K8s ConfigMap / Secret / Deployment / Service / NetworkPolicy
```

## API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/merchants?campus={campus}&sort_by={sort}&date={date}` | 前台下單頁商家清單 | No |
| GET | `/merchants/{id}` | 前台商家詳情 | No |
| GET | `/merchants/{id}/menus` | 前台商家菜單 | No |
| POST | `/merchants/apply` | 申請入駐平台 | merchant role |
| GET | `/merchants/me` | 取得商家資訊 | merchant role |
| PUT | `/merchants/me` | 更新商家資訊 | merchant role |
| POST | `/merchants/menu` | 新增菜品 | merchant role（已核准）|
| POST | `/merchants/menu/images` | 上傳菜品圖片（回傳 imageUrl） | merchant role（已核准）|
| GET | `/merchants/menu` | 列出自己的菜品 | merchant role |
| PUT | `/merchants/menu/{id}` | 更新菜品 | merchant role（已核准）|
| DELETE | `/merchants/menu/{id}` | 刪除菜品 | merchant role（已核准）|
| GET | `/merchants/orders/today` | 今日訂單彙整 | merchant role（已核准）|
| POST | `/merchants/orders/confirm-today` | 確認今日所有待處理訂單 | merchant role（已核准）|
| GET | `/health/live` | Liveness probe | No |
| GET | `/health/ready` | Readiness probe（含 DB 連線確認）| No |

## Merchant Audit Status

| 狀態碼 | 說明 | 可執行操作 |
|--------|------|-----------|
| `0` | 待審核（Pending） | 僅查看商家資訊 |
| `1` | 已核准（Approved） | 菜單管理 + 查看 / 確認訂單 |
| `2` | 已駁回（Rejected） | 僅查看商家資訊 |

## Architecture

此服務是 KuberEats 微服務架構的一部分：

```
Frontend (nginx) ─┬→ auth-service        /auth/*
                  ├→ merchant-service    /merchants, /merchants/*   ← 本服務
                  ├→ committee-service   /committee/*
                  └→ order-service       /orders/*
```

- **JWT**: auth-service 負責發 token，本服務只驗證（共用同一個 `JWT_SECRET_KEY`）
- **DB**: 本服務管理 `merchant_info`、`menu` 表，讀寫 `orders`、`order_items` 表

## Merchant Flow

```
1. 註冊商家帳號:    POST /auth/register {role: "merchant"}   (auth-service)
2. 登入取得 token:  POST /auth/login                         (auth-service)
3. 申請入駐:        POST /merchants/apply {merchantName, ...}
4. 等待福委會核准   (committee-service)
5. 管理菜單:        POST/PUT/DELETE /merchants/menu
6. 查看今日訂單:    GET  /merchants/orders/today
7. 確認今日訂單:    POST /merchants/orders/confirm-today
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
uv run python scripts/migrate.py
uv run uvicorn app.main:app --reload
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL 連線字串 | `postgresql://localhost/kubereats` |
| `JWT_SECRET_KEY` | JWT 密鑰（需與 auth-service 一致） | `dev-secret-key` |
| `JWT_ALGORITHM` | JWT 演算法 | `HS256` |
| `TIMEZONE` | 業務時區（定義「今日訂單」的日界） | `Asia/Taipei` |
| `GCS_BUCKET` | 存放菜品圖片的 GCS bucket（需開放 allUsers objectViewer） | `kubereats-menu-images` |
| `GCP_PROJECT` | GCP 專案 ID（留空則由憑證推斷） | （空） |
| `GOOGLE_APPLICATION_CREDENTIALS` | service-account 金鑰 JSON 路徑（地端認證用） | （空） |

> **注意**：`JWT_SECRET_KEY` 必須與 auth-service 使用相同的值，否則 token 驗證會失敗。

> **圖片儲存**：菜品圖片上傳至 GCP Cloud Storage，回傳公開 URL `https://storage.googleapis.com/<bucket>/<merchant_id>/<uuid>.<ext>`。
> bucket 需授予 `allUsers` 的 `roles/storage.objectViewer` 才能讓瀏覽器直接讀取。
> 地端 K8s 無法使用 Workload Identity，須將 service-account 金鑰 JSON 以 Secret 掛載，並用 `GOOGLE_APPLICATION_CREDENTIALS` 指向它。

## Testing

```bash
uv sync
uv run pytest tests/ -v
```

測試使用真實 PostgreSQL，需要先確保 `DATABASE_URL` 指向可連線的資料庫。
每個測試結束後透過 transaction rollback 自動還原，不會互相影響。

## Deployment（GCP + Kubernetes）

```bash
# 1. 替換 k8s/merchant-service.yaml 裡的 image 路徑
#    image: asia-east1-docker.pkg.dev/PROJECT_ID/kubereats/merchant-service:latest

# 2. 更新 Secret 裡的 DATABASE_URL 和 JWT_SECRET_KEY，
#    並在 ConfigMap 設定 GCS_BUCKET / GCP_PROJECT

# 3. 用下載的 service-account 金鑰建立 Secret（不要把金鑰 commit 進 repo）
kubectl create secret generic merchant-gcp-sa-key \
  --from-file=key.json=/path/to/your-sa-key.json

# 4. 套用設定
kubectl apply -f k8s/merchant-service.yaml
```

## Response Examples

### POST /merchants/apply

```json
{
  "id": 1,
  "userId": 3,
  "merchantName": "好吃便當",
  "campus": "竹科",
  "category": "便當",
  "rating": 0,
  "orderCount": 0,
  "minOrder": 100,
  "maxOrderQuantity": 50,
  "deliveryTime": "11:30-12:30",
  "tags": ["便當", "台式"],
  "auditStatus": 0,
  "createdAt": "2026-05-14T10:00:00Z",
  "updatedAt": "2026-05-14T10:00:00Z"
}
```

### GET /merchants/orders/today

```json
{
  "date": "2026-05-14",
  "totalOrders": 15,
  "totalAmount": 1850.0,
  "items": [
    {
      "menuId": 1,
      "itemName": "招牌便當",
      "totalQuantity": 10,
      "totalAmount": 1200.0
    },
    {
      "menuId": 2,
      "itemName": "雞腿飯",
      "totalQuantity": 5,
      "totalAmount": 650.0
    }
  ]
}
```

### POST /merchants/orders/confirm-today

```json
{
  "confirmed_count": 15
}
```
