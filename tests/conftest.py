import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql://postgres:test@localhost:5432/testdb"
)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import kubereats  # noqa: F401 - register all models
from app.repo.user_repo import UserRepository
from app.services.auth_service import AuthService

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def auth_service(db):
    return AuthService(user_repo=UserRepository(db))
