"""
Run pending SQL migrations against the configured database.

Usage:
    uv run python scripts/migrate.py

For SQLite (used in tests), falls back to SQLAlchemy create_all so no SQL
files are needed.  For PostgreSQL (staging / production), every *.sql file
under migrations/ is executed in alphabetical order; already-applied files
are skipped via the schema_migrations tracking table.
"""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import create_engine, text  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.database import Base  # noqa: E402
from app.models import kubereats  # noqa: E402, F401

MIGRATIONS_DIR = REPO_ROOT / "migrations"

CREATE_TRACKING_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename   VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
"""


def run_sqlite(engine) -> None:
    """SQLite: just let SQLAlchemy create every table from the ORM models."""
    Base.metadata.create_all(bind=engine)
    print("SQLite: tables created via SQLAlchemy.")


def run_postgres(engine) -> None:
    """PostgreSQL: apply each migration file that has not been applied yet."""
    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    if not sql_files:
        print("No migration files found in migrations/.")
        return

    with engine.begin() as conn:
        conn.execute(text(CREATE_TRACKING_TABLE))

        applied = {
            row[0]
            for row in conn.execute(text("SELECT filename FROM schema_migrations"))
        }

        for sql_file in sql_files:
            if sql_file.name in applied:
                print(f"  skip  {sql_file.name} (already applied)")
                continue

            print(f"  apply {sql_file.name} ...")
            conn.execute(text(sql_file.read_text(encoding="utf-8")))
            conn.execute(
                text("INSERT INTO schema_migrations (filename) VALUES (:name)"),
                {"name": sql_file.name},
            )
            print(f"  done  {sql_file.name}")


def main() -> None:
    settings = get_settings()
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False}
        if settings.database_url.startswith("sqlite")
        else {},
    )

    if engine.dialect.name == "sqlite":
        run_sqlite(engine)
    elif engine.dialect.name == "postgresql":
        run_postgres(engine)
    else:
        raise RuntimeError(f"Unsupported database dialect: {engine.dialect.name}")


if __name__ == "__main__":
    main()
