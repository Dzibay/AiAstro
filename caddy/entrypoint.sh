#!/bin/sh
set -eu

HOST=$(printf '%s' "${PUBLIC_BASE_URL}" | sed -E 's#^[a-zA-Z][a-zA-Z0-9+.-]*://##' | sed -E 's#[/:].*##')
if [ -z "$HOST" ]; then
  echo "PUBLIC_BASE_URL не содержит хост" >&2
  exit 1
fi

mkdir -p /etc/caddy

if [ "$HOST" = "localhost" ] || [ "$HOST" = "127.0.0.1" ]; then
  cat > /etc/caddy/Caddyfile <<EOF
{
	auto_https off
}
:80 {
	encode gzip
	reverse_proxy nginx:80
}
EOF
else
  cat > /etc/caddy/Caddyfile <<EOF
${HOST} {
	encode gzip
	reverse_proxy nginx:80
}
EOF
fi

exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
