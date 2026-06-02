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

    # ── GCP Cloud Storage (menu images) ──
    # Bucket must grant allUsers objectViewer so uploaded objects are publicly
    # readable at https://storage.googleapis.com/<bucket>/<key>.
    gcs_bucket: str = "kubereats-menu-images"
    # GCP project id. Leave empty to let the credentials/ADC infer it.
    gcp_project: str = ""
    # Credentials are resolved via Application Default Credentials. On-prem,
    # set GOOGLE_APPLICATION_CREDENTIALS to the mounted service-account key.


@lru_cache
def get_settings() -> Settings:
    return Settings()
