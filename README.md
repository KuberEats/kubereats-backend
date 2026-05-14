# KuberEats Auth Service

認證服務 — 負責使用者註冊、登入、JWT token 發放與刷新。

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy
- **Auth**: JWT (PyJWT) + bcrypt
- **Package Manager**: uv
- **Python**: 3.12

## Project Structure

```
app/
├── main.py                  # FastAPI entry point (auth_router only)
├── database.py              # SQLAlchemy engine & session
├── core/
│   ├── security.py          # JWT sign/verify, bcrypt hash/verify
│   └── dependencies.py      # get_current_user, require_role
├── models/
│   └── kubereats.py         # UserInfo, RefreshToken
├── schemas/
│   └── auth.py              # Request/Response schemas
├── repo/
│   └── user_repo.py         # User & token CRUD
├── services/
│   └── auth_service.py      # Register, login, refresh logic
└── routes/
    └── auth_route.py        # Auth API endpoints
```

## API Endpoints

| Method | Path              | Description        | Auth Required |
|--------|-------------------|--------------------|---------------|
| POST   | `/auth/register`  | 註冊新使用者        | No            |
| POST   | `/auth/login`     | 登入，取得 JWT token | No            |
| POST   | `/auth/refresh`   | 刷新 access token   | No            |
| GET    | `/auth/me`        | 取得目前使用者資訊    | Yes           |

## User Roles

| 角色 | 說明 |
|------|------|
| `employee` | 一般員工（訂餐） |
| `merchant` | 商家（管理菜單） |
| `committee` | 福委會（審核商家） |

## Architecture

此服務是 KuberEats 微服務架構的一部分：

```
Frontend (nginx) ─┬→ auth-service        /auth/*              ← 本服務
                  ├→ merchant-service    /merchants/apply, /me, /menu
                  ├→ committee-service   /committee/*
                  └→ order-service       /merchants (瀏覽), /orders/*
                          │
                    共用 PostgreSQL
```

- **JWT**: 本服務負責發 token，其他服務使用同一個 `JWT_SECRET_KEY` 驗證 token
- **DB**: 共用資料庫，本服務管理 `user_info` 和 `refresh_tokens` 表

## Auth Flow

```
Register: POST /auth/register {username, password, role}
    → bcrypt hash password → save to DB → return user info

Login: POST /auth/login {username, password}
    → verify password → issue access_token (30min) + refresh_token (7d)

Protected API: Header → Authorization: Bearer <access_token>
    → decode JWT → inject current user

Token Refresh: POST /auth/refresh {refreshToken}
    → validate refresh_token → issue new token pair → revoke old refresh_token
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
| `JWT_SECRET_KEY` | JWT 密鑰（所有服務須一致） | `your-secret-key` |
| `JWT_ALGORITHM` | JWT 演算法 | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token 過期時間（分鐘） | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token 過期時間（天） | `7` |

### Docker

```bash
docker-compose up auth-service
```

## Response Example

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
