-- Rename menu.image_id to image_url and widen it to hold full object URLs.
-- The column was previously unused (always NULL), so this rename is safe.
ALTER TABLE menu RENAME COLUMN image_id TO image_url;
ALTER TABLE menu ALTER COLUMN image_url TYPE VARCHAR(512);
