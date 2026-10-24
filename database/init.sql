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

-- Подтверждённая почта: кабинет открывается после перехода по ссылке из письма. Кабинеты, заведённые
-- до подтверждения почты, засчитываются подтверждёнными в день регистрации (разово, когда столбец появляется).
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'email_confirmed_at') THEN ALTER TABLE users ADD COLUMN email_confirmed_at TIMESTAMPTZ; UPDATE users SET email_confirmed_at = created_at; END IF; END $$;

-- Ссылки подтверждения почты. Хранится только хеш. email — подтверждаемый адрес: при смене почты в профиле
-- он новый и встаёт в кабинет только после перехода. next — страница кабинета, куда вести после подтверждения.
CREATE TABLE IF NOT EXISTS email_confirms (
    token_hash TEXT PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    next TEXT NOT NULL DEFAULT '',
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS email_confirms_user_idx ON email_confirms (user_id, created_at);

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
-- Знакомство с кабинетом, пройденное этим человеком: туры (tour:intro, tour:sky) и шаги «Пути новичка»
-- (step:sun, step:chat). Хранятся в аккаунте, чтобы не зависеть от браузера.
ALTER TABLE users ADD COLUMN IF NOT EXISTS marks TEXT[] NOT NULL DEFAULT '{}';

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

-- Отправленное приглашение — уже согласие показать партнёру свои данные; так считаются и прежние приглашения.
UPDATE partners SET share_at = created_at WHERE invite_token IS NOT NULL AND share_at IS NULL;
-- Партнёр, уже открывший свой кабинет, получает эти данные на свою сторону пары.
UPDATE partners o SET birth_date = u.birth_date, birth_time = u.birth_time, birth_place = u.birth_place, birth_lat = u.birth_lat, birth_lon = u.birth_lon, birth_tz = u.birth_tz, filled_at = now(), news = 'filled', news_at = now() FROM users u, partners m WHERE o.linked_user_id = u.id AND m.user_id = u.id AND m.pair_id = o.pair_id AND m.invite_token IS NOT NULL AND m.share_at IS NOT NULL AND u.birth_date IS NOT NULL AND o.birth_date IS NULL;

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

-- Реферальные ссылки рекламных кампаний: <адрес сайта>/?ref=<token> на любой странице.
-- Удалённая ссылка уносит свои переходы; люди, пришедшие по ней, остаются без метки.
CREATE TABLE IF NOT EXISTS ref_links (
    id BIGSERIAL PRIMARY KEY,
    token TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ref_links_token_key ON ref_links (token);
-- Сколько потрачено на кампанию всего, в рублях: для окупаемости в «Деньгах по источникам».
ALTER TABLE ref_links ADD COLUMN IF NOT EXISTS spend INTEGER NOT NULL DEFAULT 0;

-- Посетители: анонимный id, который браузер хранит в localStorage (не cookie). ref_id — первая
-- реферальная ссылка, по которой он пришёл: ей навсегда засчитываются его регистрация и оплаты.
-- visits — визиты: новый начинается после получаса тишины или с переходом по ссылке.
-- Удаление кабинета уносит его браузеры и все его события (accounts._remove): счётчики пересчитываются.
CREATE TABLE IF NOT EXISTS visitors (
    id TEXT PRIMARY KEY,
    ref_id BIGINT REFERENCES ref_links (id) ON DELETE SET NULL,
    user_id BIGINT REFERENCES users (id) ON DELETE SET NULL,
    source TEXT NOT NULL DEFAULT '',
    landing TEXT NOT NULL DEFAULT '',
    device TEXT NOT NULL DEFAULT '',
    visits INTEGER NOT NULL DEFAULT 1,
    first_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS visitors_first_idx ON visitors (first_at);
CREATE INDEX IF NOT EXISTS visitors_ref_idx ON visitors (ref_id);
CREATE INDEX IF NOT EXISTS visitors_user_idx ON visitors (user_id);

-- События для статистики: visit (начало визита), view (страница — имя маршрута), ref (переход по
-- реферальной ссылке), signup, confirm (почта подтверждена по ссылке), birth (дата рождения сохранена впервые), tour (name — тур и исход:
-- section-chart:done, intro:skip; value — шаг), goal (цель лендинга), click (кнопка с data-track),
-- scroll (name — страница, value — глубина 25/50/75/100), time (name — страница, value — секунды
-- внимания), act (действие: game:play, game:land; value — шаг или секунды), offer (показ предложения
-- <продукт>:<место>), pick (выбор срока «Небосвода», value — месяцы).
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    visitor_id TEXT REFERENCES visitors (id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users (id) ON DELETE SET NULL,
    ref_id BIGINT REFERENCES ref_links (id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    value INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS events_kind_idx ON events (kind, created_at);
CREATE INDEX IF NOT EXISTS events_user_idx ON events (user_id, created_at);
-- Календарь активности в карточке: страницы браузера, уже привязанного к аккаунту.
CREATE INDEX IF NOT EXISTS events_visitor_idx ON events (visitor_id, created_at) WHERE visitor_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS events_ref_idx ON events (ref_id, created_at) WHERE ref_id IS NOT NULL;
-- Страница, на которой случилось действие (click, scroll, offer…): у view она в name.
ALTER TABLE events ADD COLUMN IF NOT EXISTS page TEXT NOT NULL DEFAULT '';

-- Откуда пришёл человек: его браузер при регистрации и реферальная ссылка этого браузера.
ALTER TABLE users ADD COLUMN IF NOT EXISTS visitor_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS ref_id BIGINT REFERENCES ref_links (id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS users_ref_idx ON users (ref_id);
CREATE INDEX IF NOT EXISTS users_visitor_idx ON users (visitor_id) WHERE visitor_id IS NOT NULL;

-- Разовая уборка следов кабинетов, удалённых до того, как удаление стало уносить статистику:
-- регистрация без аккаунта отмечает браузер удалённого — он уходит со своими страницами и переходами,
-- если им не пользуется живой аккаунт. Туры бывают только в кабинете, без аккаунта они тоже чужие.
DELETE FROM visitors v USING events e WHERE e.kind = 'signup' AND e.user_id IS NULL AND e.visitor_id = v.id AND v.user_id IS NULL AND NOT EXISTS (SELECT 1 FROM users u WHERE u.visitor_id = v.id) AND NOT EXISTS (SELECT 1 FROM events o WHERE o.visitor_id = v.id AND o.user_id IS NOT NULL);
DELETE FROM events WHERE user_id IS NULL AND kind IN ('signup', 'tour');
-- Кампания платежа — ссылка плательщика в момент оплаты: доход остаётся за ней и после удаления кабинета.
ALTER TABLE payments ADD COLUMN IF NOT EXISTS ref_id BIGINT REFERENCES ref_links (id) ON DELETE SET NULL;
UPDATE payments p SET ref_id = u.ref_id FROM users u WHERE p.user_id = u.id AND p.ref_id IS NULL AND u.ref_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS payments_ref_idx ON payments (ref_id) WHERE ref_id IS NOT NULL;
-- Предложение, с которого человек пришёл к оплате: sky:chat, sky:forecast, pair:panel… (пусто — неизвестно).
ALTER TABLE payments ADD COLUMN IF NOT EXISTS place TEXT NOT NULL DEFAULT '';

-- Отметки чек-листа дня: какие задачи прогноза человек выполнил в этот день.
CREATE TABLE IF NOT EXISTS day_tasks (
    user_id BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    day DATE NOT NULL,
    done TEXT[] NOT NULL DEFAULT '{}',
    PRIMARY KEY (user_id, day)
);

-- ИИ-астролог. У каждой реплики — тема, которую ей дала проверка или модель:
-- astro, smalltalk, offtopic, injection, abuse, crisis; pending — ответ ещё пишется; пусто — реплика до ИИ.
-- counted — вопрос идёт в счёт пробных и дневных (уводы в сторону и кризис не считаются).
-- source ответа: ai — модель, stub — шаблоны, guard — готовый текст сервиса.
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT '';
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS counted BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT '';
-- Три увода в сторону за полчаса — разговор на паузе до этого момента.
ALTER TABLE users ADD COLUMN IF NOT EXISTS chat_pause_until TIMESTAMPTZ;

-- Что человек сам рассказал ИИ-астрологу о себе (до 12 коротких фактов): они идут в каждый
-- следующий разговор. Оператор видит и стирает их в карточке человека; удаление кабинета стирает всё.
CREATE TABLE IF NOT EXISTS chat_memory (
    user_id BIGINT PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    facts JSONB NOT NULL DEFAULT '[]',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Каждое обращение к модели и каждый готовый ответ сервиса: тема, модель, токены, цена в рублях, время.
-- kind: chat — разговор человека, playground — проба в админке, redteam — проверка провокациями, check — проверка связи.
-- Расход остаётся и после удаления кабинета (ссылка пустеет): по нему считается месячный бюджет.
-- flagged — ответ модели не прошёл проверку хотя бы раз; note — вопрос проб из админки (не из разговоров людей).
CREATE TABLE IF NOT EXISTS ai_runs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users (id) ON DELETE SET NULL,
    message_id BIGINT REFERENCES chat_messages (id) ON DELETE SET NULL,
    kind TEXT NOT NULL DEFAULT 'chat',
    category TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL DEFAULT '',
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    cached_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost NUMERIC(12, 4) NOT NULL DEFAULT 0,
    ms INTEGER NOT NULL DEFAULT 0,
    error TEXT NOT NULL DEFAULT '',
    flagged BOOLEAN NOT NULL DEFAULT FALSE,
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ai_runs_created_idx ON ai_runs (created_at);
CREATE INDEX IF NOT EXISTS ai_runs_user_idx ON ai_runs (user_id, created_at) WHERE user_id IS NOT NULL;

-- Журнал ошибок для оператора (админка → «Ошибки»): что сломалось на сервере (back) и в браузерах
-- посетителей (front). Одна и та же ошибка из одного места — одна строка (signature) со счётчиком.
-- returned — ошибка повторилась после отметки «исправлено». Исправленные старше 90 дней удаляются.
CREATE TABLE IF NOT EXISTS faults (
    id BIGSERIAL PRIMARY KEY,
    signature TEXT NOT NULL UNIQUE,
    side TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL DEFAULT '',
    place TEXT NOT NULL DEFAULT '',
    path TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT '',
    agent TEXT NOT NULL DEFAULT '',
    user_id BIGINT REFERENCES users (id) ON DELETE SET NULL,
    count INTEGER NOT NULL DEFAULT 1,
    returned BOOLEAN NOT NULL DEFAULT FALSE,
    first_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS faults_last_idx ON faults (last_at DESC);

-- Копии базы на Яндекс Диск: каждая попытка — строка. ok пусто, пока копия делается;
-- при запуске backend незаконченные отмечаются прерванными. Строки старше 180 дней удаляются.
CREATE TABLE IF NOT EXISTS backup_runs (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    manual BOOLEAN NOT NULL DEFAULT FALSE,
    ok BOOLEAN,
    name TEXT NOT NULL DEFAULT '',
    size BIGINT,
    error TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS backup_runs_started_idx ON backup_runs (started_at DESC);

-- Журнал писем: каждое письмо сайта — строка. status: sending → sent | failed (error — почему) |
-- off (почта не настроена). Кнопка письма ведёт через /api/site/go/<token>: clicks — сколько раз
-- нажали, clicked_at — когда впервые. Письма человека живут, пока жив кабинет; пробные письма
-- оператора (user_id пуст) стираются через 90 дней.
CREATE TABLE IF NOT EXISTS letters (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users (id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    email TEXT NOT NULL,
    subject TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'sending',
    error TEXT NOT NULL DEFAULT '',
    token TEXT UNIQUE,
    clicks INTEGER NOT NULL DEFAULT 0,
    clicked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS letters_user_idx ON letters (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS letters_created_idx ON letters (created_at DESC);

-- Письмо о незавершённой оплате уходит по платежу не больше одного раза.
ALTER TABLE payments ADD COLUMN IF NOT EXISTS reminded_at TIMESTAMPTZ;

INSERT INTO app_settings (key, value) VALUES
    ('site_name', 'Астра'),
    ('tagline', 'Натальная карта обычным языком'),
    ('support_email', ''),
    ('receipt_vat_code', '1')
ON CONFLICT (key) DO NOTHING;
