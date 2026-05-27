ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS order_number VARCHAR(32),
    ADD COLUMN IF NOT EXISTS service_date DATE,
    ADD COLUMN IF NOT EXISTS scheduled_for TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS dispatch_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS schedule_status VARCHAR(32) NOT NULL DEFAULT 'not_scheduled',
    ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(255),
    ADD COLUMN IF NOT EXISTS idempotency_request_hash VARCHAR(64),
    ADD COLUMN IF NOT EXISTS released_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS cancellation_reason TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_order_number
    ON orders (order_number)
    WHERE order_number IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_user_id_idempotency_key
    ON orders (user_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS outbox_events (
    id SERIAL PRIMARY KEY,
    aggregate_type VARCHAR(64) NOT NULL,
    aggregate_id INTEGER NOT NULL,
    event_type VARCHAR(128) NOT NULL,
    payload_json JSON NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    published_at TIMESTAMPTZ,
    retry_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_outbox_events_available_unpublished
    ON outbox_events (available_at, id)
    WHERE published_at IS NULL;
