from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import create_engine  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.database import Base  # noqa: E402
from app.models import notification  # noqa: E402,F401


POSTGRES_MIGRATION = Path("migrations/001_create_notification_tables.sql")


def main() -> None:
    settings = get_settings()
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False}
        if settings.database_url.startswith("sqlite")
        else {},
    )

    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(bind=engine)
        return

    if engine.dialect.name == "postgresql":
        migration_sql = POSTGRES_MIGRATION.read_text(encoding="utf-8")
        with engine.begin() as connection:
            connection.exec_driver_sql(migration_sql)
        return

    raise RuntimeError(f"Unsupported database dialect for migrations: {engine.dialect.name}")


if __name__ == "__main__":
    main()
