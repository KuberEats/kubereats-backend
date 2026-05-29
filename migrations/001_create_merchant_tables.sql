CREATE TABLE IF NOT EXISTS user_info (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50)  NOT NULL UNIQUE,
    email           VARCHAR(255) UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    role            VARCHAR(20)  NOT NULL,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_user_info_username ON user_info(username);
CREATE INDEX IF NOT EXISTS ix_user_info_email    ON user_info(email);

CREATE TABLE IF NOT EXISTS merchant_info (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER       NOT NULL UNIQUE REFERENCES user_info(id) ON DELETE CASCADE,
    merchant_name       VARCHAR(100)  NOT NULL,
    campus              VARCHAR(20)   NOT NULL,
    category            VARCHAR(50)   NOT NULL,
    rating              NUMERIC(2,1)  NOT NULL DEFAULT 0,
    order_count         INTEGER       NOT NULL DEFAULT 0,
    min_order           NUMERIC(10,2) NOT NULL DEFAULT 0,
    max_order_quantity  INTEGER       NOT NULL DEFAULT 0,
    delivery_time       VARCHAR(50)   NOT NULL,
    tags                JSONB         NOT NULL DEFAULT '[]',
    audit_status        INTEGER       NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_merchant_info_user_id      ON merchant_info(user_id);
CREATE INDEX IF NOT EXISTS ix_merchant_info_audit_status ON merchant_info(audit_status);

CREATE TABLE IF NOT EXISTS menu (
    id                  SERIAL PRIMARY KEY,
    merchant_id         INTEGER       NOT NULL REFERENCES merchant_info(id) ON DELETE CASCADE,
    item_name           VARCHAR(100)  NOT NULL,
    price               NUMERIC(10,2) NOT NULL,
    max_daily_quantity  INTEGER       NOT NULL DEFAULT 0,
    image_id            VARCHAR(255),
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_menu_merchant_id ON menu(merchant_id);

CREATE TABLE IF NOT EXISTS orders (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER       NOT NULL REFERENCES user_info(id),
    total_amount NUMERIC(10,2) NOT NULL,
    order_status INTEGER       NOT NULL DEFAULT 0,
    order_time   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_orders_user_id    ON orders(user_id);
CREATE INDEX IF NOT EXISTS ix_orders_order_time ON orders(order_time);

CREATE TABLE IF NOT EXISTS order_items (
    id         SERIAL PRIMARY KEY,
    order_id   INTEGER       NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    menu_id    INTEGER       NOT NULL REFERENCES menu(id),
    quantity   INTEGER       NOT NULL,
    unit_price NUMERIC(10,2) NOT NULL,
    subtotal   NUMERIC(10,2) NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS ix_order_items_menu_id  ON order_items(menu_id);
