# KuberEats DB Roles

KuberEats uses separate database roles for application runtime, read-only
inspection, controlled seed-data work, and DBA operations. Human users must not
reuse the application role.

## Roles

| Role | Purpose | Allowed |
| --- | --- | --- |
| `kubereats_app` | Backend runtime | Application-owned queries only |
| `qa_readonly` | Engineer/QA/DBA inspection | `CONNECT`, schema `USAGE`, `SELECT` |
| `qa_seed` | Non-production seed data | `SELECT` and limited `INSERT/UPDATE/DELETE` on business tables |
| `migration_user` | Migration automation, if configured | Managed by migration flow only |
| DBA/admin role | Emergency DBA work | DBA-controlled; do not create casually |

Do not create a broad `db_admin` role unless a DBA policy and owner already
exist. Use existing DBA access for emergency changes.

## Role Creation Script

The reviewed SQL lives at:

```text
scripts/db/create_qa_roles.sql
```

It is idempotent and does not store passwords. Passwords are passed with psql
variables:

```bash
export QA_READONLY_PASSWORD='<from-secret-store>'
export QA_SEED_PASSWORD='<from-secret-store>'

psql -h 127.0.0.1 -p 15432 -d kubereats \
  -U <approved_admin_or_migration_role> \
  -v QA_READONLY_PASSWORD="$QA_READONLY_PASSWORD" \
  -v QA_SEED_PASSWORD="$QA_SEED_PASSWORD" \
  -f scripts/db/create_qa_roles.sql
```

If a password variable is omitted, the script leaves that role's password
unchanged.

## Current Schema Scope

Reconnaissance found the application schema is `public` in database
`kubereats`. Current business tables include:

- `finance`
- `menu`
- `menu_daily_capacity`
- `merchant_info`
- `order_items`
- `orders`
- `refresh_tokens`
- `reservation_capacity_slots`
- `reservation_request_items`
- `reservation_requests`
- `tags`
- `user_info`
- `user_tags`

`qa_seed` is deliberately not granted DML on `schema_migrations`,
`outbox_events`, or `reservation_outbox_events`.

## Production Rules

- Do not run role DDL in production without a ticket, SQL review, backup plan,
  and rollback plan.
- Do not run seed scripts in production.
- Do not give test users write access to production.
- Do not grant `CREATE`, `ALTER`, `DROP`, `CREATEDB`, `CREATEROLE`,
  `SUPERUSER`, or replication privileges to QA roles.
- Do not store passwords in Git, shell scripts, Kubernetes manifests, or docs.

## Read-Only Usage

Open the SSH tunnel from `docs/ops/db-access.md`, then connect with:

```bash
psql -h 127.0.0.1 -p 15432 -d kubereats -U qa_readonly
```

Example safe checks:

```sql
select current_database(), current_user, pg_is_in_recovery();
select count(*) from public.orders;
```

## Seed Usage

Use `qa_seed` only in dev, staging, or acceptance environments. Prefer seed
scripts, backend APIs, or admin UI workflows over manual SQL.

When SQL is necessary:

1. Open a ticket or work item.
2. Confirm target environment is not production.
3. Review the SQL with an engineer or DBA.
4. Run inside a transaction when practical.
5. Verify through the application/API.
6. Record the executed SQL or seed script revision in the ticket.
