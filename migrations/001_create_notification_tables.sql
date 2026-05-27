CREATE TABLE IF NOT EXISTS notification_requests (
    id VARCHAR(36) PRIMARY KEY,
    template_key VARCHAR(120) NOT NULL,
    template_version INTEGER NOT NULL,
    source_service VARCHAR(80) NOT NULL,
    recipient_type VARCHAR(40) NOT NULL,
    recipient_id VARCHAR(120) NOT NULL,
    recipient_email VARCHAR(320) NOT NULL,
    recipient_name VARCHAR(120),
    locale VARCHAR(20) NOT NULL,
    payload JSONB NOT NULL,
    idempotency_key VARCHAR(200) NOT NULL UNIQUE,
    payload_hash VARCHAR(64) NOT NULL,
    correlation_id VARCHAR(120) NOT NULL,
    status VARCHAR(20) NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    provider_message_id VARCHAR(200),
    created_at TIMESTAMPTZ NOT NULL,
    queued_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    last_error_code VARCHAR(80),
    last_error_message TEXT
);

CREATE INDEX IF NOT EXISTS ix_notification_requests_template_key
    ON notification_requests(template_key);
CREATE INDEX IF NOT EXISTS ix_notification_requests_source_service
    ON notification_requests(source_service);

CREATE TABLE IF NOT EXISTS notification_delivery_attempts (
    id VARCHAR(36) PRIMARY KEY,
    notification_id VARCHAR(36) NOT NULL REFERENCES notification_requests(id),
    attempt_no INTEGER NOT NULL,
    provider VARCHAR(80) NOT NULL,
    status VARCHAR(40) NOT NULL,
    error_code VARCHAR(80),
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    CONSTRAINT uq_delivery_attempt_no UNIQUE(notification_id, attempt_no)
);

CREATE INDEX IF NOT EXISTS ix_notification_delivery_attempts_notification_id
    ON notification_delivery_attempts(notification_id);
