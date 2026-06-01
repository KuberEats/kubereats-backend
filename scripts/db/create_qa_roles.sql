-- KuberEats QA/DBA access roles.
--
-- Purpose:
-- - qa_readonly: read-only troubleshooting and reporting.
-- - qa_seed: controlled seed-data maintenance in non-production environments.
--
-- This script is idempotent and intentionally does not contain passwords.
-- Provide passwords with psql variables when a password rotation is required:
--
--   psql -d kubereats \
--     -v QA_READONLY_PASSWORD="$QA_READONLY_PASSWORD" \
--     -v QA_SEED_PASSWORD="$QA_SEED_PASSWORD" \
--     -f scripts/db/create_qa_roles.sql
--
-- Do not run against production without a reviewed change ticket, backup plan,
-- and explicit approval.

\set ON_ERROR_STOP on

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qa_readonly') THEN
    CREATE ROLE qa_readonly LOGIN;
    COMMENT ON ROLE qa_readonly IS 'Read-only KuberEats troubleshooting role; no DML or DDL.';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qa_seed') THEN
    CREATE ROLE qa_seed LOGIN;
    COMMENT ON ROLE qa_seed IS 'Non-production seed-data role; limited DML on business tables; no DDL.';
  END IF;
END
$$;

\if :{?QA_READONLY_PASSWORD}
ALTER ROLE qa_readonly PASSWORD :'QA_READONLY_PASSWORD';
\else
\echo 'QA_READONLY_PASSWORD not set; leaving qa_readonly password unchanged.'
\endif

\if :{?QA_SEED_PASSWORD}
ALTER ROLE qa_seed PASSWORD :'QA_SEED_PASSWORD';
\else
\echo 'QA_SEED_PASSWORD not set; leaving qa_seed password unchanged.'
\endif

-- Keep both roles out of schema/object ownership and DDL paths.
ALTER ROLE qa_readonly NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
ALTER ROLE qa_seed NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM qa_readonly;
REVOKE CREATE ON SCHEMA public FROM qa_seed;

GRANT CONNECT ON DATABASE kubereats TO qa_readonly, qa_seed;
GRANT USAGE ON SCHEMA public TO qa_readonly, qa_seed;

-- Read-only role: SELECT only.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO qa_readonly;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO qa_readonly;
ALTER DEFAULT PRIVILEGES FOR ROLE kubereats_app IN SCHEMA public
  GRANT SELECT ON TABLES TO qa_readonly;
ALTER DEFAULT PRIVILEGES FOR ROLE kubereats_app IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO qa_readonly;

-- Seed role: SELECT plus constrained DML on application business tables.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO qa_seed;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO qa_seed;

GRANT INSERT, UPDATE, DELETE ON TABLE
  public.finance,
  public.menu,
  public.menu_daily_capacity,
  public.merchant_info,
  public.order_items,
  public.orders,
  public.refresh_tokens,
  public.reservation_capacity_slots,
  public.reservation_request_items,
  public.reservation_requests,
  public.tags,
  public.user_info,
  public.user_tags
TO qa_seed;

GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO qa_seed;

ALTER DEFAULT PRIVILEGES FOR ROLE kubereats_app IN SCHEMA public
  GRANT SELECT ON TABLES TO qa_seed;
ALTER DEFAULT PRIVILEGES FOR ROLE kubereats_app IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO qa_seed;

-- Explicitly avoid migration and outbox writes from human seed users.
REVOKE INSERT, UPDATE, DELETE ON TABLE
  public.schema_migrations,
  public.outbox_events,
  public.reservation_outbox_events
FROM qa_seed;
