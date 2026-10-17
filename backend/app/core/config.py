from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SECRET = "dev-only-secret-change-me-0123456789abcdef"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="UNILOAD_", extra="ignore")

    env: str = "dev"  # dev | test | prod

    # Ilova cheklangan `uniload_app` roli bilan ulanadi (RLS ishlaydi).
    database_url: str = "postgresql+psycopg://uniload_app:uniload_app@localhost:5433/uniload"
    # Migratsiya va bootstrap jadval egasi `uniload` roli bilan.
    migration_database_url: str = "postgresql+psycopg://uniload:uniload@localhost:5433/uniload"
    redis_url: str = "redis://localhost:6380/0"

    jwt_secret: str = _DEV_SECRET
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 14
    password_reset_ttl_minutes: int = 30
    cookie_secure: bool = False

    cors_origins: list[str] = ["http://localhost:3000"]

    max_failed_logins: int = 5
    lockout_minutes: int = 15

    @model_validator(mode="after")
    def _check_prod(self) -> "Settings":
        if self.env == "prod":
            if self.jwt_secret == _DEV_SECRET or len(self.jwt_secret) < 32:
                raise ValueError("UNILOAD_JWT_SECRET production uchun kamida 32 belgili maxfiy qiymat bo‘lishi kerak")
            if not self.cookie_secure:
                raise ValueError("Production’da UNILOAD_COOKIE_SECURE=true bo‘lishi shart")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
