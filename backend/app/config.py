from pathlib import Path

from psycopg.conninfo import make_conninfo
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file() -> str | None:
    for parent in Path(__file__).resolve().parents:
        if (parent / "docker-compose.yml").exists():
            env = parent / ".env"
            return str(env) if env.exists() else None
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    site_name: str = "Астра"
    public_base_url: str = "http://localhost"

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "aiastro"
    db_user: str = "aiastro"
    db_password: str = ""

    web_session_secret: str = ""
    admin_session_secret: str = ""
    admin_password: str = ""
    session_ttl_seconds: int = 1_209_600

    # Подсказки городов: публичный Nominatim разрешает запрос в секунду и просит контакт.
    geocoder_url: str = "https://nominatim.openstreetmap.org/search"
    geocoder_contact: str = ""
    geocoder_interval: float = 1.0

    # Эфемериды JPL DE421 (1900–2050); пусто — backend/data, в образе /app/data.
    ephemeris_dir: str = ""

    # Копии базы: WebDAV Яндекс Диска и pg_dump (в образе backend — postgresql-client-16).
    backup_webdav_url: str = "https://webdav.yandex.ru"
    backup_pg_dump: str = "pg_dump"

    @property
    def dsn(self) -> str:
        # make_conninfo экранирует значения: пароль с @, /, : или пробелами не ломает строку.
        return make_conninfo(
            host=self.db_host,
            port=self.db_port,
            dbname=self.db_name,
            user=self.db_user,
            password=self.db_password,
        )


settings = Settings()
