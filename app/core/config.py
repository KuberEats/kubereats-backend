from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "notification-service"
    database_url: str = "sqlite:///./notification.db"
    redis_url: str = "redis://localhost:6379/0"
    internal_service_tokens: str = Field(
        default=(
            "order-service:dev-order-token,"
            "finance-service:dev-finance-token,"
            "merchant-service:dev-merchant-token,"
            "committee-service:dev-committee-token,"
            "admin-service:dev-admin-token"
        )
    )
    email_provider: str = "local"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from_email: str = "noreply@kubereats.local"
    max_delivery_attempts: int = 4
    rate_limit_per_minute: int = 120

    @property
    def service_token_map(self) -> dict[str, str]:
        tokens: dict[str, str] = {}
        for item in self.internal_service_tokens.split(","):
            if not item.strip() or ":" not in item:
                continue
            service, token = item.split(":", 1)
            tokens[token.strip()] = service.strip()
        return tokens


@lru_cache
def get_settings() -> Settings:
    return Settings()
