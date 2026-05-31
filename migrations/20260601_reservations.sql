CREATE TABLE IF NOT EXISTS reservation_requests (
    id SERIAL PRIMARY KEY,
    reservation_token VARCHAR(64) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES user_info(id),
    merchant_id INTEGER NOT NULL REFERENCES merchant_info(id),
    service_date DATE NOT NULL,
    pickup_slot VARCHAR(64) NOT NULL DEFAULT '',
    pickup_option VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING_RESERVATION',
    idempotency_key VARCHAR(255),
    idempotency_request_hash VARCHAR(64),
    failure_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    lease_until TIMESTAMPTZ,
    retry_count INTEGER NOT NULL DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_reservation_requests_reservation_token
    ON reservation_requests (reservation_token);

CREATE UNIQUE INDEX IF NOT EXISTS uq_reservation_requests_user_id_idempotency_key
    ON reservation_requests (user_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_reservation_requests_status_created_at
    ON reservation_requests (status, created_at);

CREATE INDEX IF NOT EXISTS ix_reservation_requests_lease_until
    ON reservation_requests (lease_until);

CREATE TABLE IF NOT EXISTS reservation_request_items (
    id SERIAL PRIMARY KEY,
    reservation_request_id INTEGER NOT NULL REFERENCES reservation_requests(id),
    menu_item_id INTEGER NOT NULL REFERENCES menu(id),
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2),
    subtotal NUMERIC(10, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reservation_capacity_slots (
    id SERIAL PRIMARY KEY,
    merchant_id INTEGER NOT NULL REFERENCES merchant_info(id),
    menu_item_id INTEGER NOT NULL REFERENCES menu(id),
    service_date DATE NOT NULL,
    pickup_slot VARCHAR(64) NOT NULL DEFAULT '',
    total_capacity INTEGER NOT NULL,
    reserved_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_reservation_capacity_total_nonnegative CHECK (total_capacity >= 0),
    CONSTRAINT ck_reservation_capacity_reserved_nonnegative CHECK (reserved_count >= 0),
    CONSTRAINT ck_reservation_capacity_not_oversold CHECK (reserved_count <= total_capacity)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_reservation_capacity_slot_key
    ON reservation_capacity_slots (
        merchant_id,
        menu_item_id,
        service_date,
        pickup_slot
    );

CREATE INDEX IF NOT EXISTS ix_reservation_capacity_lookup
    ON reservation_capacity_slots (
        merchant_id,
        menu_item_id,
        service_date,
        pickup_slot
    );

CREATE TABLE IF NOT EXISTS reservation_outbox_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(128) NOT NULL,
    aggregate_type VARCHAR(64) NOT NULL,
    aggregate_id INTEGER NOT NULL,
    payload JSON NOT NULL,
    ordering_key VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    retry_count INTEGER NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at TIMESTAMPTZ,
    last_error TEXT,
    CONSTRAINT ck_reservation_outbox_retry_count_nonnegative CHECK (retry_count >= 0)
);

CREATE INDEX IF NOT EXISTS ix_reservation_outbox_status_next_retry
    ON reservation_outbox_events (status, next_retry_at, id);
