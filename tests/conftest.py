import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql://postgres:test@localhost:5432/testdb"
)
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ["DATABASE_URL"]


@pytest.fixture(scope="session")
def create_tables():
    from app.database import Base
    from app.models import kubereats  # noqa: F401 - register all models

    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db(create_tables):
    engine = create_engine(DATABASE_URL)
    TestingSessionLocal = sessionmaker(bind=engine)
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.expire_all()
            session.begin_nested()

    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def auth_service(db):
    from app.repo.user_repo import UserRepository
    from app.services.auth_service import AuthService

    return AuthService(user_repo=UserRepository(db))
