ALTER TABLE merchant_info
    ADD COLUMN IF NOT EXISTS cooperation_start_date DATE;

ALTER TABLE merchant_info
    ADD COLUMN IF NOT EXISTS cooperation_end_date DATE;

ALTER TABLE merchant_info
    ADD COLUMN IF NOT EXISTS suspended_at TIMESTAMPTZ;

ALTER TABLE merchant_info
    ADD COLUMN IF NOT EXISTS suspension_reason TEXT;
