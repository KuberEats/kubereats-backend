from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "merchant-service"
    database_url: str = "postgresql://localhost/kubereats"
    jwt_secret_key: str = "dev-secret-key"
    jwt_algorithm: str = "HS256"
    # Business timezone used to define a calendar day (e.g. "today's orders").
    timezone: str = "Asia/Taipei"

    # ── MinIO / object storage ──
    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "kubereats"
    # Public base URL for building image links. Falls back to minio_endpoint
    # when empty (useful when the browser-facing host differs from the
    # in-cluster endpoint the service uploads through).
    minio_public_url: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
