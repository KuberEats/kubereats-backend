# KuberEats Merchant Service

商家管理服務 — 負責商家入駐申請、商家資訊管理、菜單 CRUD、今日訂單彙整。

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy
- **Auth**: JWT (PyJWT) — 僅驗證 token，不發 token
- **Package Manager**: uv
- **Python**: 3.12

## Project Structure

```
app/
├── main.py                      # FastAPI entry point (merchant_router only)
├── database.py                  # SQLAlchemy engine & session
├── core/
│   ├── security.py              # JWT decode (verify only, no token creation)
│   └── dependencies.py          # get_current_user, require_role
├── models/
│   └── kubereats.py             # UserInfo, MerchantInfo, Menu, Order, OrderItem
├── schemas/
│   └── merchant.py              # Merchant, Menu, OrderSummary schemas
├── repo/
│   └── merchant_repo.py         # Merchant, menu CRUD & order summary query
├── services/
│   └── merchant_service.py      # Apply, menu CRUD, order summary logic
└── routes/
    └── merchant_route.py        # Merchant API endpoints
```

## API Endpoints

| Method | Path                      | Description        | Auth                    |
|--------|---------------------------|--------------------|-------------------------|
| POST   | `/merchants/apply`        | 申請入駐平台        | merchant role           |
| GET    | `/merchants/me`           | 取得商家資訊        | merchant role           |
| PUT    | `/merchants/me`           | 更新商家資訊        | merchant role           |
| POST   | `/merchants/menu`         | 新增菜品           | merchant role (已核准)   |
| GET    | `/merchants/menu`         | 列出自己的菜品      | merchant role           |
| PUT    | `/merchants/menu/{id}`    | 更新菜品           | merchant role (已核准)   |
| DELETE | `/merchants/menu/{id}`    | 刪除菜品           | merchant role (已核准)   |
| GET    | `/merchants/orders/today` | 今日訂單彙整        | merchant role (已核准)   |

## Merchant Audit Status

| 狀態碼 | 說明 | 可執行操作 |
|--------|------|-----------|
| `0`    | 待審核 (Pending) | 僅查看商家資訊 |
| `1`    | 已核准 (Approved) | 菜單管理 + 查看訂單 |
| `2`    | 已駁回 (Rejected) | 僅查看商家資訊 |

## Architecture

此服務是 KuberEats 微服務架構的一部分：

```
Frontend (nginx) ─┬→ auth-service        /auth/*
                  ├→ merchant-service    /merchants/apply, /me, /menu  ← 本服務
                  ├→ committee-service   /committee/*
                  └→ order-service       /merchants (瀏覽), /orders/*
                          │
                    共用 PostgreSQL
```

- **JWT**: auth-service 負責發 token，本服務僅驗證 token（共用同一個 `JWT_SECRET_KEY`）
- **DB**: 共用資料庫，本服務管理 `merchant_info`、`menu` 表，讀取 `orders`、`order_items` 表

## Merchant Flow

```
1. 註冊商家帳號:  POST /auth/register {role: "merchant"}  (auth-service)
2. 登入取得 token: POST /auth/login                       (auth-service)
3. 申請入駐:      POST /merchants/apply {merchantName, campus, ...}
4. 等待福委會核准  (committee-service)
5. 管理菜單:      POST/PUT/DELETE /merchants/menu
6. 查看今日訂單:   GET /merchants/orders/today
```

## Setup

### Prerequisites

- Python 3.12+
- PostgreSQL
- [uv](https://docs.astral.sh/uv/)

### Install & Run

```bash
pip install uv
uv sync
uv run uvicorn app.main:app --reload
```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL 連線字串 | `postgresql://orderdev:orderdev@localhost:5432/order_system` |
| `JWT_SECRET_KEY` | JWT 密鑰（需與 auth-service 一致） | `your-secret-key` |
| `JWT_ALGORITHM` | JWT 演算法 | `HS256` |

### Docker

```bash
docker-compose up merchant-service
```

## Response Example

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
