"""
Тестовая инфраструктура: фикстуры для SQLite in-memory и FastAPI TestClient.
"""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.main import app
from app.seeds.operation_types import seed_operation_types
from app.seeds.return_reasons import seed_return_reasons


# SQLite in-memory для тестов
TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
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
    # Импортируем все модели чтобы Base.metadata знал о них
    import app.models.receipt  # noqa: F401
    import app.models.employee  # noqa: F401
    import app.models.operation  # noqa: F401
    import app.models.polishing  # noqa: F401
    import app.models.return_  # noqa: F401
    import app.models.history  # noqa: F401
    import app.models.notification  # noqa: F401

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
def client(db_session: Session) -> TestClient:
    """FastAPI TestClient с подменённой БД."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_client(seeded_db: Session) -> TestClient:
    """FastAPI TestClient с засеянными справочниками."""
    def override_get_db():
        try:
            yield seeded_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


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
