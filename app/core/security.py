import jwt

from app.core.config import get_settings

_settings = get_settings()
SECRET_KEY = _settings.jwt_secret_key
ALGORITHM = _settings.jwt_algorithm


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
