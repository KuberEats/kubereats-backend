from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "verification"
    app_env: str = "local"
    log_level: str = "info"
    port: int = 8000

    database_url: str = "postgresql://localhost/kubereats"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    auto_create_tables: bool = True

    jwt_secret_key: str = "dev-secret-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    mailgun_api_key: str = ""
    mailgun_domain: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
