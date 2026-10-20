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

-- Письма о сроке «Небосвода» и об ответе партнёра; человек отключает их в кабинете.
ALTER TABLE users ADD COLUMN IF NOT EXISTS mail_notes BOOLEAN NOT NULL DEFAULT TRUE;
-- Срок «Небосвода», о конце которого уже напомнили: новая оплата меняет sky_until, и напоминание придёт снова.
ALTER TABLE users ADD COLUMN IF NOT EXISTS sky_reminded TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS users_email_key ON users (email);

-- Ссылки для нового пароля. Хранится только хеш: сама ссылка есть лишь в письме. Ссылка
-- разовая и живёт час; новый пароль гасит все ссылки человека.
CREATE TABLE IF NOT EXISTS password_resets (
    token_hash TEXT PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS password_resets_user_idx ON password_resets (user_id, created_at);

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

-- Сколько раз человек сам исправил свои данные рождения: одна правка, дальше — через поддержку.
-- Иначе одна покупка разбора открывала бы любые пары с любыми датами.
ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_edits INTEGER NOT NULL DEFAULT 0;

-- Пара — общая для двоих. Строка partners — сторона пары в кабинете одного человека: у пары по
-- приглашению, когда партнёр завёл кабинет, сторон две, у введённой вручную — одна. Покупка
-- принадлежит паре: разбор открыт обеим сторонам и остаётся у той, что не удаляла пару.
CREATE TABLE IF NOT EXISTS pairs (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE partners ADD COLUMN IF NOT EXISTS pair_id BIGINT REFERENCES pairs (id) ON DELETE CASCADE;
-- Кабинет партнёра, связанный с этой стороной. Данные рождения в строке — его, скопированные с его согласия.
ALTER TABLE partners ADD COLUMN IF NOT EXISTS linked_user_id BIGINT REFERENCES users (id) ON DELETE SET NULL;
-- Согласие хозяина строки показать партнёру свои данные рождения (галочка у приглашения).
ALTER TABLE partners ADD COLUMN IF NOT EXISTS joined_at TIMESTAMPTZ;
ALTER TABLE partners ADD COLUMN IF NOT EXISTS share_at TIMESTAMPTZ;
-- Хеш ключа, который получил заполнивший приглашение без кабинета: по нему пара привяжется к его новому кабинету.
ALTER TABLE partners ADD COLUMN IF NOT EXISTS claim_hash TEXT;
-- Знак в кабинете: filled, linked, bought, gift, left — гаснет, когда человек открыл пару.
ALTER TABLE partners ADD COLUMN IF NOT EXISTS news TEXT NOT NULL DEFAULT '';
ALTER TABLE partners ADD COLUMN IF NOT EXISTS news_at TIMESTAMPTZ;

-- Партнёры, заведённые до общих пар: каждому своя пара.
DO $$ DECLARE r RECORD; pid BIGINT; BEGIN FOR r IN SELECT id, created_at FROM partners WHERE pair_id IS NULL LOOP INSERT INTO pairs (created_at) VALUES (r.created_at) RETURNING id INTO pid; UPDATE partners SET pair_id = pid WHERE id = r.id; END LOOP; END $$;

CREATE INDEX IF NOT EXISTS partners_pair_idx ON partners (pair_id);
CREATE INDEX IF NOT EXISTS partners_linked_idx ON partners (linked_user_id);

-- Разовые покупки: их записывает оплата или оператор в админке. Сумм здесь нет, они в payments.
-- Разбор пары принадлежит паре (pair_id); user_id — кто заплатил, source — pay или admin.
-- Удалённая сторона или кабинет не стирают покупку: она остаётся у второй стороны.
CREATE TABLE IF NOT EXISTS purchases (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users (id) ON DELETE SET NULL,
    product TEXT NOT NULL,
    partner_id BIGINT REFERENCES partners (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE purchases ADD COLUMN IF NOT EXISTS pair_id BIGINT REFERENCES pairs (id) ON DELETE CASCADE;
ALTER TABLE purchases ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'pay';
ALTER TABLE purchases ALTER COLUMN user_id DROP NOT NULL;
DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'purchases_user_id_fkey' AND confdeltype = 'c') THEN ALTER TABLE purchases DROP CONSTRAINT purchases_user_id_fkey; ALTER TABLE purchases ADD CONSTRAINT purchases_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL; END IF; END $$;
UPDATE purchases pu SET pair_id = p.pair_id FROM partners p WHERE pu.pair_id IS NULL AND pu.partner_id = p.id;
DROP INDEX IF EXISTS purchases_partner_key;
CREATE UNIQUE INDEX IF NOT EXISTS purchases_pair_key ON purchases (product, pair_id) WHERE pair_id IS NOT NULL;

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

-- Пара, за которую платят: сторона может исчезнуть, пока человек на странице ЮKassa, пара — нет.
ALTER TABLE payments ADD COLUMN IF NOT EXISTS pair_id BIGINT REFERENCES pairs (id) ON DELETE SET NULL;
UPDATE payments pa SET pair_id = p.pair_id FROM partners p WHERE pa.pair_id IS NULL AND pa.partner_id = p.id;

CREATE UNIQUE INDEX IF NOT EXISTS payments_yookassa_key ON payments (yookassa_id);
CREATE INDEX IF NOT EXISTS payments_user_idx ON payments (user_id, created_at);

INSERT INTO app_settings (key, value) VALUES
    ('site_name', 'Астра'),
    ('tagline', 'Натальная карта обычным языком'),
    ('support_email', ''),
    ('receipt_vat_code', '1')
ON CONFLICT (key) DO NOTHING;
