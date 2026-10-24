FROM python:3.12-slim

WORKDIR /app

# pg_dump для ежедневных копий базы на Яндекс Диск: версия не ниже сервера (postgres:16),
# поэтому из репозитория PostgreSQL, а не из Debian.
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-common ca-certificates \
    && /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y \
    && apt-get install -y --no-install-recommends postgresql-client-16 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Эфемериды JPL DE421 (1900–2050, 17 МБ) — в образ, чтобы первая карта не ждала загрузки.
RUN python -c "from skyfield.api import Loader; Loader('/app/data', verbose=False)('de421.bsp')"

COPY backend/app /app/app
COPY backend/run_api.py /app/run_api.py
COPY database /app/database

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
