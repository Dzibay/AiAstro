-- Схема Астры. Файл выполняется целиком при каждом старте backend.
-- Денег в этой версии нет: колонок с суммами нет, float не используется.

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS name TEXT NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE UNIQUE INDEX IF NOT EXISTS users_email_key ON users (email);

INSERT INTO app_settings (key, value) VALUES
    ('site_name', 'Астра'),
    ('tagline', 'Натальная карта обычным языком'),
    ('support_email', '')
ON CONFLICT (key) DO NOTHING;
