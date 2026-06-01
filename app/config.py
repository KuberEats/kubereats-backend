from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    queue_backend: str = "fake"
    cors_allow_origins: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "https://api.kubereats.click/,"
        "https://kubereats.click/"
    )
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    dispatch_lead_minutes: int = 30
    max_schedule_days: int = 30

    gcp_project_id: str = ""
    gcp_location: str = ""
    gcp_cloud_tasks_queue: str = ""
    gcp_task_handler_url: str = ""
    gcp_task_service_account_email: str = ""

    internal_task_auth_enabled: bool = False
    internal_task_token: str = ""
    internal_task_handler_url: str = "http://backend:8000/internal/tasks/orders/release"

    reservation_queue_mode: str = "local"
    pubsub_topic_reservation_requested: str = ""
    reservation_outbox_max_retries: int = 10
    reservation_processing_lease_seconds: int = 300
    reservation_db_polling_batch_size: int = 25
    order_consumer_poll_interval_seconds: float = 2.0

    @property
    def cors_origins(self) -> list[str]:
        origins = [origin.strip().rstrip("/") for origin in self.cors_allow_origins.split(",")]
        return [origin for origin in origins if origin]


@lru_cache
def get_settings() -> Settings:
    return Settings()
