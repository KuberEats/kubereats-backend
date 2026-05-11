# KuberEats Backend - Authentication Module

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy
- **Auth**: JWT (PyJWT) + bcrypt
- **Package Manager**: uv
- **Python**: 3.12

## Project Structure

```
app/
├── main.py                  # FastAPI entry point
├── database.py              # SQLAlchemy engine & session
├── core/
│   ├── security.py          # JWT sign/verify, bcrypt hash
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
    └── auth_route.py        # API endpoints
```

## API Endpoints

| Method | Path              | Description              | Auth Required |
|--------|-------------------|--------------------------|---------------|
| POST   | `/auth/register`  | Register a new user      | No            |
| POST   | `/auth/login`     | Login, returns JWT tokens| No            |
| POST   | `/auth/refresh`   | Refresh access token     | No            |
| GET    | `/auth/me`        | Get current user info    | Yes           |

## User Roles

- `employee` - Regular employee
- `merchant` - Restaurant merchant
- `committee` - Welfare committee member

## Setup

### 1. Prerequisites

- Python 3.12+
- PostgreSQL
- [uv](https://docs.astral.sh/uv/)

### 2. Install Dependencies

```bash
pip install uv
uv sync
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your database connection:

```
DATABASE_URL=postgresql://<user>:<password>@localhost:<port>/<dbname>
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 4. Start PostgreSQL (Docker)

```bash
docker run -d --name kubereats-pg \
  -e POSTGRES_USER=orderdev \
  -e POSTGRES_PASSWORD=orderdev \
  -e POSTGRES_DB=order_system \
  -p 5432:5432 \
  postgres:16-alpine
```

### 5. Run Server

```bash
uv run uvicorn app.main:app --reload
```

### 6. Test

Open http://localhost:8000/docs for Swagger UI.

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
