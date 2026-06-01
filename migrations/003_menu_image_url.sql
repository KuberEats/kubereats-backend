ALTER TABLE menu
    ADD COLUMN IF NOT EXISTS image_url VARCHAR(255);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'menu'
          AND column_name = 'image_id'
    ) THEN
        EXECUTE 'UPDATE menu SET image_url = COALESCE(image_url, image_id)';
    END IF;
END $$;
