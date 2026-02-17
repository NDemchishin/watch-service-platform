"""
Тестовая инфраструктура: фикстуры для SQLite in-memory и FastAPI TestClient.
"""
import os

# Отключаем Telegram бота при тестах — должно быть ДО импорта app/telegram_bot
os.environ.pop("TELEGRAM_BOT_TOKEN", None)
os.environ.pop("TELEGRAM_BOT_WEBHOOK_URL", None)
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["TELEGRAM_BOT_WEBHOOK_URL"] = ""
os.environ["API_KEY"] = "test-api-key"
os.environ["TELEGRAM_WEBHOOK_SECRET"] = "test-webhook-secret"
os.environ["DATABASE_URL"] = "sqlite://"

# Принудительно обнуляем config бота (мог быть уже загружен с реальным TOKEN)
import telegram_bot.config
telegram_bot.config.bot_config.TOKEN = ""
telegram_bot.config.bot_config.WEBHOOK_URL = ""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.main import app as fastapi_app
from app.seeds.operation_types import seed_operation_types
from app.seeds.return_reasons import seed_return_reasons

# Импортируем все модели чтобы Base.metadata знал о них
import app.models.receipt  # noqa: F401
import app.models.employee  # noqa: F401
import app.models.operation  # noqa: F401
import app.models.polishing  # noqa: F401
import app.models.return_  # noqa: F401
import app.models.history  # noqa: F401
import app.models.notification  # noqa: F401


# SQLite in-memory с StaticPool — одна БД для всех connections
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Включаем поддержку FK в SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture(autouse=True)
def setup_database():
    """Создаёт все таблицы перед каждым тестом и удаляет после."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Session:
    """Фикстура тестовой сессии БД."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seeded_db(db_session: Session) -> Session:
    """Сессия с засеянными справочниками (operation_types, return_reasons)."""
    seed_operation_types(db_session)
    seed_return_reasons(db_session)
    return db_session


@pytest.fixture
def client_no_auth(db_session: Session) -> TestClient:
    """FastAPI TestClient БЕЗ API-ключа (для тестов безопасности)."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app, raise_server_exceptions=False) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def client(db_session: Session) -> TestClient:
    """FastAPI TestClient с подменённой БД и API-ключом."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(
        fastapi_app,
        raise_server_exceptions=False,
        headers={"X-API-Key": "test-api-key"},
    ) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def seeded_client(seeded_db: Session) -> TestClient:
    """FastAPI TestClient с засеянными справочниками и API-ключом."""
    def override_get_db():
        try:
            yield seeded_db
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(
        fastapi_app,
        raise_server_exceptions=False,
        headers={"X-API-Key": "test-api-key"},
    ) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


# --- Вспомогательные функции для создания тестовых данных ---

def create_receipt(c: TestClient, receipt_number: str = "TEST-001") -> dict:
    """Создаёт квитанцию через API."""
    resp = c.post("/api/v1/receipts", json={"receipt_number": receipt_number})
    assert resp.status_code == 201
    return resp.json()


def create_employee(c: TestClient, name: str = "Тестовый Мастер", telegram_id: int = None) -> dict:
    """Создаёт сотрудника через API."""
    data = {"name": name}
    if telegram_id is not None:
        data["telegram_id"] = telegram_id
    resp = c.post("/api/v1/employees", json=data)
    assert resp.status_code == 201
    return resp.json()
