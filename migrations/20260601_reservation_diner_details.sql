ALTER TABLE reservation_requests
    ADD COLUMN IF NOT EXISTS comments TEXT;

ALTER TABLE reservation_requests
    ADD COLUMN IF NOT EXISTS diner_name VARCHAR(100);

ALTER TABLE reservation_requests
    ADD COLUMN IF NOT EXISTS diner_phone VARCHAR(32);
