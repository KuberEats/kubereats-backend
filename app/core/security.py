from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


@dataclass(frozen=True)
class ServicePrincipal:
    source_service: str


def authenticate_service(authorization: str | None = Header(default=None)) -> ServicePrincipal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    source_service = get_settings().service_token_map.get(token)
    if source_service is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service token")
    return ServicePrincipal(source_service=source_service)
