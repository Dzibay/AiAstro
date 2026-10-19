-- Схема Астры. Файл выполняется целиком при каждом старте backend.
-- Суммы — целые рубли (INTEGER), float не используется.

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

-- Данные рождения: дата и место, время может быть неизвестно.
ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_date DATE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_time TIME;
ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_place TEXT NOT NULL DEFAULT '';
-- Координаты города из подсказок (5 знаков — около метра) и его часовой пояс IANA.
-- Если город введён вручную без подсказки, координат нет: карта попросит уточнить.
ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_lat NUMERIC(7, 5);
ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_lon NUMERIC(8, 5);
ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_tz TEXT NOT NULL DEFAULT '';
-- Когда человек дал согласие на обработку персональных данных (галочка при регистрации).
ALTER TABLE users ADD COLUMN IF NOT EXISTS consent_at TIMESTAMPTZ;
-- Подписка «Небосвод» действует до этого момента; NULL — подписки нет. Её продлевает оплата или оператор в админке.
ALTER TABLE users ADD COLUMN IF NOT EXISTS sky_until TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS users_email_key ON users (email);

-- Посчитанные натальные карты. Ключ — хеш данных рождения и версии расчёта: исправленные
-- данные или новая версия просто не находят старую строку, её можно удалить в любой момент.
CREATE TABLE IF NOT EXISTS charts (
    key TEXT PRIMARY KEY,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Готовые тексты толкований. Ключ — хеш входа (что толкуем и версия текстов), а не человек:
-- одинаковые положения у разных людей читают одну строку, новая версия текстов пишет новые.
CREATE TABLE IF NOT EXISTS readings (
    kind TEXT NOT NULL,
    key TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (kind, key)
);

-- Партнёры для совместимости. Данные вводит сам человек или партнёр по ссылке-приглашению:
-- пока ссылка не заполнена, даты рождения нет. consent_at — согласие партнёра, давшего данные сам.
CREATE TABLE IF NOT EXISTS partners (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    birth_date DATE,
    birth_time TIME,
    birth_place TEXT NOT NULL DEFAULT '',
    birth_lat NUMERIC(7, 5),
    birth_lon NUMERIC(8, 5),
    birth_tz TEXT NOT NULL DEFAULT '',
    invite_token TEXT,
    consent_at TIMESTAMPTZ,
    filled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS partners_invite_key ON partners (invite_token);
CREATE INDEX IF NOT EXISTS partners_user_idx ON partners (user_id, created_at);

-- Разовые покупки: их записывает оплата или оператор в админке. Сумм здесь нет, они в payments.
-- Удалённый партнёр не стирает покупку: ссылка на него просто становится пустой.
CREATE TABLE IF NOT EXISTS purchases (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    product TEXT NOT NULL,
    partner_id BIGINT REFERENCES partners (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS purchases_partner_key ON purchases (user_id, product, partner_id) WHERE partner_id IS NOT NULL;

-- Разговор с астрологом: вопросы человека (role = 'user') и ответы (role = 'astrologer').
-- Пробные вопросы без «Небосвода» считаются по этой же таблице.
CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS chat_messages_user_idx ON chat_messages (user_id, id);

-- Платежи ЮKassa. Строка создаётся до перехода на страницу оплаты (status = 'new'), получает
-- id ЮKassa ('pending') и закрывается ответом ЮKassa: 'succeeded' — покупка применена ровно один
-- раз, 'canceled' — не прошла, 'failed' — ЮKassa не приняла сам запрос. days — срок «Небосвода».
-- Удалённый кабинет не стирает платёж (учёт хранится пять лет): ссылка становится пустой,
-- остаётся почта, на которую ушёл чек.
CREATE TABLE IF NOT EXISTS payments (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users (id) ON DELETE SET NULL,
    email TEXT NOT NULL DEFAULT '',
    product TEXT NOT NULL,
    partner_id BIGINT REFERENCES partners (id) ON DELETE SET NULL,
    days INTEGER NOT NULL DEFAULT 0,
    amount INTEGER NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    yookassa_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    paid_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS payments_yookassa_key ON payments (yookassa_id);
CREATE INDEX IF NOT EXISTS payments_user_idx ON payments (user_id, created_at);

INSERT INTO app_settings (key, value) VALUES
    ('site_name', 'Астра'),
    ('tagline', 'Натальная карта обычным языком'),
    ('support_email', ''),
    ('receipt_vat_code', '1')
ON CONFLICT (key) DO NOTHING;
