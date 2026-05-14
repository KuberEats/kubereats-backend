# KuberEats Committee Service

福委會審核服務 — 負責審核商家的入駐申請（核准 / 駁回）。

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy
- **Auth**: JWT (PyJWT) — 僅驗證 token，不發 token
- **Package Manager**: uv
- **Python**: 3.12

## Project Structure

```
app/
├── main.py                      # FastAPI entry point (committee_router only)
├── database.py                  # SQLAlchemy engine & session
├── core/
│   ├── security.py              # JWT decode (verify only, no token creation)
│   └── dependencies.py          # get_current_user, require_role
├── models/
│   └── kubereats.py             # UserInfo, MerchantInfo
├── schemas/
│   └── committee.py             # MerchantReviewResponse, AuditResultResponse
├── repo/
│   └── committee_repo.py        # Merchant audit queries & status update
├── services/
│   └── committee_service.py     # Approve / reject logic
└── routes/
    └── committee_route.py       # Committee API endpoints
```

## API Endpoints

| Method | Path                                    | Description        | Auth           |
|--------|-----------------------------------------|--------------------|----------------|
| GET    | `/committee/merchants/pending`          | 列出待審核商家       | committee role |
| GET    | `/committee/merchants`                  | 列出所有商家         | committee role |
| PATCH  | `/committee/merchants/{id}/approve`     | 核准商家             | committee role |
| PATCH  | `/committee/merchants/{id}/reject`      | 駁回商家             | committee role |

## Audit Status

| 狀態碼 | 說明 |
|--------|------|
| `0`    | 待審核 (Pending) |
| `1`    | 已核准 (Approved) |
| `2`    | 已駁回 (Rejected) |

僅待審核 (`audit_status = 0`) 的商家可以被審核，已審核的商家會回傳 400 錯誤。

## Architecture

此服務是 KuberEats 微服務架構的一部分：

```
Frontend (nginx) ─┬→ auth-service        /auth/*
                  ├→ merchant-service    /merchants/apply, /me, /menu
                  ├→ committee-service   /committee/*        ← 本服務
                  └→ order-service       /merchants (瀏覽), /orders/*
                          │
                    共用 PostgreSQL
```

- **JWT**: auth-service 負責發 token，本服務僅驗證 token（共用同一個 `JWT_SECRET_KEY`）
- **DB**: 共用資料庫，本服務只讀寫 `merchant_info` 的 `audit_status` 欄位

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
docker-compose up committee-service
```

## Response Example

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
