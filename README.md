# KuberEats Backend - Committee Management Module

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy
- **Auth**: JWT (PyJWT) + bcrypt
- **Package Manager**: uv
- **Python**: 3.12

## Project Structure

```
app/
├── main.py                      # FastAPI entry point
├── database.py                  # SQLAlchemy engine & session
├── core/
│   ├── security.py              # JWT sign/verify, bcrypt hash
│   └── dependencies.py          # get_current_user, require_role
├── models/
│   └── kubereats.py             # UserInfo, RefreshToken, MerchantInfo, Menu, Order, OrderItem
├── schemas/
│   ├── auth.py                  # Auth request/response schemas
│   ├── merchant.py              # Merchant & menu schemas
│   └── committee.py             # Committee audit schemas
├── repo/
│   ├── user_repo.py             # User & token CRUD
│   ├── merchant_repo.py         # Merchant, menu CRUD & order summary
│   └── committee_repo.py        # Merchant audit queries & status update
├── services/
│   ├── auth_service.py          # Register, login, refresh logic
│   ├── merchant_service.py      # Apply, menu CRUD, order summary
│   └── committee_service.py     # Merchant audit approve/reject logic
└── routes/
    ├── auth_route.py            # Auth API endpoints
    ├── merchant_route.py        # Merchant API endpoints
    └── committee_route.py       # Committee API endpoints
```

## API Endpoints

### Auth

| Method | Path              | Description              | Auth Required |
|--------|-------------------|--------------------------|---------------|
| POST   | `/auth/register`  | Register a new user      | No            |
| POST   | `/auth/login`     | Login, returns JWT tokens| No            |
| POST   | `/auth/refresh`   | Refresh access token     | No            |
| GET    | `/auth/me`        | Get current user info    | Yes           |

### Merchant

| Method | Path                     | Description                | Auth           |
|--------|--------------------------|----------------------------|----------------|
| POST   | `/merchants/apply`       | Apply to join platform     | merchant role  |
| GET    | `/merchants/me`          | Get own merchant info      | merchant role  |
| PUT    | `/merchants/me`          | Update merchant info       | merchant role  |
| POST   | `/merchants/menu`        | Add menu item              | merchant role (approved) |
| GET    | `/merchants/menu`        | List own menu items        | merchant role  |
| PUT    | `/merchants/menu/{id}`   | Update menu item           | merchant role (approved) |
| DELETE | `/merchants/menu/{id}`   | Delete menu item           | merchant role (approved) |
| GET    | `/merchants/orders/today`| Today's order summary      | merchant role (approved) |

### Committee

| Method | Path                                    | Description              | Auth            |
|--------|-----------------------------------------|--------------------------|-----------------|
| GET    | `/committee/merchants/pending`          | List pending merchants   | committee role  |
| GET    | `/committee/merchants`                  | List all merchants       | committee role  |
| PATCH  | `/committee/merchants/{id}/approve`     | Approve a merchant       | committee role  |
| PATCH  | `/committee/merchants/{id}/reject`      | Reject a merchant        | committee role  |

## Audit Status

- `0` - Pending (waiting for committee approval)
- `1` - Approved (merchant can manage menu and view orders)
- `2` - Rejected

Only pending merchants (`audit_status = 0`) can be reviewed. Already reviewed merchants return 400 error.

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

Edit `.env`:

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

## Full Flow

```
1. Register merchant:  POST /auth/register {role: "merchant"}
2. Register committee: POST /auth/register {role: "committee"}
3. Merchant login → apply to platform: POST /merchants/apply
4. Committee login → review: GET /committee/merchants/pending
5. Committee approves: PATCH /committee/merchants/1/approve
6. Merchant can now manage menu: POST /merchants/menu
7. Merchant views daily orders: GET /merchants/orders/today
```
