from pathlib import Path

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

    @property
    def dsn(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
