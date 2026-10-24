#!/bin/sh
set -eu

SCHEME=$(printf '%s' "${PUBLIC_BASE_URL}" | sed -nE 's#^([a-zA-Z][a-zA-Z0-9+.-]*)://.*#\1#p' | tr 'A-Z' 'a-z')
HOST=$(printf '%s' "${PUBLIC_BASE_URL}" | sed -E 's#^[a-zA-Z][a-zA-Z0-9+.-]*://##' | sed -E 's#[/:].*##')
if [ -z "$HOST" ]; then
  echo "PUBLIC_BASE_URL не содержит хост" >&2
  exit 1
fi

mkdir -p /etc/caddy

# Заголовки безопасности для всех ответов. Встраивать сайт во фрейм можно только себе и Вебвизору
# Метрики (он показывает записи визитов во фрейме), MIME-типы не угадываются, чужим сайтам уходит
# только домен, а не адрес страницы; камера, микрофон и геолокация сайту не нужны.
SECURITY='header {
		X-Content-Type-Options "nosniff"
		Referrer-Policy "strict-origin-when-cross-origin"
		Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()"
		Content-Security-Policy "frame-ancestors '"'"'self'"'"' https://metrika.yandex.ru https://metrika.yandex.by https://metrica.yandex.com https://metrica.yandex.com.tr https://webvisor.com https://*.webvisor.com"
		-Server
	}'

# Локально или явный http:// — без сертификатов, на :80 для любого Host.
if [ "$HOST" = "localhost" ] || [ "$HOST" = "127.0.0.1" ] || [ "$SCHEME" = "http" ]; then
  cat > /etc/caddy/Caddyfile <<EOF
{
	auto_https off
}
:80 {
	encode zstd gzip
	${SECURITY}
	reverse_proxy nginx:80
}
EOF
else
  GLOBAL=""
  if [ -n "${ACME_EMAIL:-}" ]; then
    GLOBAL="{
	email ${ACME_EMAIL}
}
    "
  fi
  # Канонический хост без www; www → тот же путь на канон. Иначе возврат из ЮKassa
  # на «другой» хост мог обрезаться до главной.
  APEX=$(printf '%s' "$HOST" | sed 's/^www\.//')
  cat > /etc/caddy/Caddyfile <<EOF
${GLOBAL}${APEX} {
	encode zstd gzip
	${SECURITY}
	# Браузер запоминает на год: сюда только по HTTPS.
	header Strict-Transport-Security "max-age=31536000"
	reverse_proxy nginx:80
}
www.${APEX} {
	redir https://${APEX}{uri} permanent
}
EOF
fi

exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
