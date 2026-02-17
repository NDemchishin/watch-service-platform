# Промпт 4: Исправление инфраструктуры и DX

## Контекст

Ты работаешь с проектом watch-service-platform — система учёта для часовой мастерской. Backend на FastAPI + SQLAlchemy 2.0 + PostgreSQL, Telegram-бот на aiogram 3.x. Перед началом работы ОБЯЗАТЕЛЬНО прочитай файл `CONVENTIONS.md` в корне проекта и `docs/TECHNICAL_SPECIFICATION.md`.

## Задача

Исправить ~15 инфраструктурных проблем: dead code, datetime, производительность, logging, Redis FSM.

---

## Блок 1: Dead code и naming (4 бага)

### Что сломано

1. **`backend/app/core/security.py`** — пустой файл-заглушка. (Если Промпт 3 уже выполнен — файл заполнен. Если нет — заполнить согласно Промпту 3.)
2. **`backend/app/schemas/polishing.py:28-30`** — `PolishingDetailsUpdate` определена, но нигде не используется.
3. **`backend/app/api/__init__.py:6`** — telegram router импортируется в `__init__.py` и отдельно в `main.py` с другим префиксом. Потенциальный конфликт маршрутов.
4. **`backend/app/schemas/receipt.py:31-35`** — поле `current_deadline` в `ReceiptUpdate`, но в модели Receipt поле называется `deadline`. Naming mismatch.

### Что сделать

1. **Удалить `PolishingDetailsUpdate`** из `backend/app/schemas/polishing.py` — или реализовать и подключить, если она нужна.

2. **Исправить двойной импорт telegram router:**
   - Проверить `backend/app/api/__init__.py` — если telegram router включается здесь, убрать его из `main.py` (или наоборот).
   - Должен быть ОДИН путь подключения.

3. **Унифицировать naming** — в `ReceiptUpdate` переименовать `current_deadline` → `deadline`, чтобы совпадало с моделью. Обновить все места использования.

### Файлы для изменения:
- `backend/app/schemas/polishing.py` — удалить PolishingDetailsUpdate
- `backend/app/api/__init__.py` — убрать дубль telegram router
- `backend/app/main.py` — проверить подключение роутеров
- `backend/app/schemas/receipt.py` — переименовать current_deadline → deadline
- `backend/app/api/receipts.py` — обновить использование

---

## Блок 2: Московское время (3 бага)

### Что сломано

1. Используется `datetime.utcnow()` в одних местах, `server_default=sa.text('NOW()')` в других — два источника времени.
2. `analytics_service.py:24-36` — `_period_start` использует `utcnow()`, на сервере не в UTC периоды будут неверными.
3. `datetime.utcnow()` deprecated в Python 3.12+.

### Что сделать

1. **Создать хелперы** в `backend/app/core/utils.py`:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

def now_moscow() -> datetime:
    """Текущее время в московской таймзоне. Использовать ВМЕСТО datetime.utcnow()."""
    return datetime.now(MOSCOW_TZ)

def format_datetime(dt: datetime) -> str:
    """Форматировать datetime для показа пользователю в московском времени."""
    if dt is None:
        return "—"
    moscow = dt.astimezone(MOSCOW_TZ)
    return moscow.strftime("%d.%m.%Y %H:%M")
```

2. **Добавить `MOSCOW_TZ` в config:**

```python
# backend/app/core/config.py
from zoneinfo import ZoneInfo
MOSCOW_TZ = ZoneInfo("Europe/Moscow")
```

3. **Заменить ВСЕ `datetime.utcnow()`** на `now_moscow()` в:
   - `backend/app/services/receipt_service.py`
   - `backend/app/services/polishing_service.py`
   - `backend/app/services/notification_service.py`
   - `backend/app/services/analytics_service.py`
   - `backend/app/services/history_service.py`
   - `backend/app/services/operation_service.py`
   - `backend/app/services/return_service.py`

4. **Обновить модели** — заменить `server_default=sa.text('NOW()')` на Python-side default:

```python
from app.core.utils import now_moscow

class Receipt(Base):
    created_at = Column(DateTime(timezone=True), default=now_moscow)
    updated_at = Column(DateTime(timezone=True), default=now_moscow, onupdate=now_moscow)
```

Применить ко ВСЕМ моделям:
- `backend/app/models/receipt.py`
- `backend/app/models/employee.py`
- `backend/app/models/operation.py`
- `backend/app/models/polishing.py`
- `backend/app/models/return_.py`
- `backend/app/models/history.py`
- `backend/app/models/notification.py`

5. **Обновить аналитику** — в `analytics_service.py` метод `_period_start`:

```python
def _period_start(self, period: str) -> datetime:
    now = now_moscow()
    if period == "day":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = now - timedelta(days=now.weekday())
        return start.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return datetime.min.replace(tzinfo=MOSCOW_TZ)
```

6. **Обновить бот** — в `telegram_bot/utils.py` использовать `format_datetime()` для отображения дат:

```python
from backend.app.core.utils import format_datetime
# Или дублировать хелпер в telegram_bot/utils.py чтобы не зависеть от backend
```

7. **Обновить хендлеры бота** — везде где показываются даты пользователю, использовать `format_datetime()`.

### Файлы для изменения:
- `backend/app/core/config.py` — добавить MOSCOW_TZ
- `backend/app/core/utils.py` — добавить now_moscow, format_datetime
- `backend/app/services/*.py` — ВСЕ сервисы: utcnow() → now_moscow()
- `backend/app/models/*.py` — ВСЕ модели: server_default → default=now_moscow
- `backend/app/services/analytics_service.py` — _period_start с Moscow TZ
- `telegram_bot/utils.py` — format_datetime для бота
- `telegram_bot/handlers/urgent.py` — format_datetime для отображения
- `telegram_bot/handlers/history.py` — format_datetime для отображения
- `telegram_bot/handlers/polishing.py` — format_datetime для отображения

---

## Блок 3: Производительность (3 бага)

### Что сломано

1. **`backend/app/services/analytics_service.py:320-349`** — N+1 запрос: для каждого полировщика — отдельный запрос по всем PolishingDetails. При 50 полировщиках = 51 запрос.
2. **`backend/app/core/database.py`** — нет настроек connection pooling (дефолтные значения SQLAlchemy: pool_size=5).
3. Нет индексов на FK-колонки во вторичных таблицах.

### Что сделать

1. **Переписать polishing_workload на один запрос:**

```python
def polishing_workload(self, period: str = "all"):
    period_start = self._period_start(period)

    results = (
        self.db.query(
            PolishingDetails.polisher_id,
            Employee.full_name,
            func.count(PolishingDetails.id).label("total"),
            func.count(
                case((PolishingDetails.returned_at.is_(None), 1))
            ).label("in_progress"),
            func.avg(
                case(
                    (
                        PolishingDetails.returned_at.isnot(None),
                        func.extract('epoch', PolishingDetails.returned_at - PolishingDetails.sent_at) / 3600,
                    )
                )
            ).label("avg_hours"),
        )
        .join(Employee, Employee.id == PolishingDetails.polisher_id)
        .filter(PolishingDetails.sent_at >= period_start)
        .group_by(PolishingDetails.polisher_id, Employee.full_name)
        .all()
    )
    return [
        {
            "polisher_id": r.polisher_id,
            "polisher_name": r.full_name,
            "total": r.total,
            "in_progress": r.in_progress,
            "avg_hours": round(float(r.avg_hours or 0), 1),
        }
        for r in results
    ]
```

2. **Настроить connection pooling** в `backend/app/core/database.py`:

```python
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,          # Максимум соединений в пуле
    max_overflow=20,        # Дополнительные соединения при пиковой нагрузке
    pool_pre_ping=True,     # Проверка соединения перед использованием
    pool_recycle=3600,      # Обновление соединений каждый час
)
```

3. **Добавить индексы на FK** — создать новую Alembic миграцию:

```python
# alembic/versions/003_add_fk_indexes.py

def upgrade():
    op.create_index('ix_operations_receipt_id', 'operations', ['receipt_id'])
    op.create_index('ix_operations_employee_id', 'operations', ['employee_id'])
    op.create_index('ix_operations_operation_type_id', 'operations', ['operation_type_id'])
    op.create_index('ix_returns_receipt_id', 'returns', ['receipt_id'])
    op.create_index('ix_polishing_details_receipt_id', 'polishing_details', ['receipt_id'])
    op.create_index('ix_polishing_details_polisher_id', 'polishing_details', ['polisher_id'])
    op.create_index('ix_history_events_receipt_id', 'history_events', ['receipt_id'])
    op.create_index('ix_notifications_receipt_id', 'notifications', ['receipt_id'])
    op.create_index('ix_receipts_receipt_number', 'receipts', ['receipt_number'])
    op.create_index('ix_employees_telegram_id', 'employees', ['telegram_id'])

def downgrade():
    op.drop_index('ix_operations_receipt_id')
    # ... все остальные
```

Также добавить `index=True` в определения колонок моделей:

```python
class Operation(Base):
    receipt_id = Column(Integer, ForeignKey("receipts.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
```

### Файлы для изменения:
- `backend/app/services/analytics_service.py` — один запрос вместо N+1
- `backend/app/core/database.py` — connection pooling
- `backend/alembic/versions/003_add_fk_indexes.py` — СОЗДАТЬ миграцию
- `backend/app/models/operation.py` — index=True на FK
- `backend/app/models/return_.py` — index=True на FK
- `backend/app/models/polishing.py` — index=True на FK
- `backend/app/models/history.py` — index=True на FK
- `backend/app/models/notification.py` — index=True на FK
- `backend/app/models/receipt.py` — index=True на receipt_number
- `backend/app/models/employee.py` — index=True на telegram_id

---

## Блок 4: Логирование (2 бага)

### Что сломано

1. Ни один сервис не использует `logging`. При сбое в production — ноль информации.
2. Нет health check эндпоинта с проверкой БД.

### Что сделать

1. **Добавить logging в каждый сервис:**

```python
import logging

logger = logging.getLogger(__name__)

class ReceiptService:
    def create(self, data):
        logger.info("Creating receipt: number=%s", data.receipt_number)
        # ...
        logger.info("Receipt created: id=%s, number=%s", receipt.id, receipt.receipt_number)
        return receipt

    def update_deadline(self, receipt_id, data):
        logger.info("Updating deadline: receipt_id=%s, new_deadline=%s", receipt_id, data.deadline)
        # ...
```

Применить ко ВСЕМ сервисам:
- `receipt_service.py`
- `employee_service.py`
- `operation_service.py`
- `polishing_service.py`
- `return_service.py`
- `history_service.py`
- `notification_service.py`
- `analytics_service.py`

2. **Добавить health check с проверкой БД** в `backend/app/main.py`:

```python
from sqlalchemy import text

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": str(e)},
        )
```

3. **Настроить формат логов** в `backend/app/main.py`:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
```

### Файлы для изменения:
- `backend/app/services/*.py` — ВСЕ сервисы: добавить logger
- `backend/app/main.py` — health check + logging config

---

## Блок 5: Redis FSM Storage для бота (1 баг)

### Что сломано

Бот использует `MemoryStorage` (по умолчанию в aiogram). При рестарте бота ВСЕ пользователи теряют текущее состояние — незаконченные flow обрываются.

### Что сделать

1. **Добавить `redis` и `aioredis` в зависимости** (`requirements.txt`).

2. **Обновить `telegram_bot/bot.py`:**

```python
from aiogram.fsm.storage.redis import RedisStorage
from telegram_bot.config import settings

# Вместо:
# dp = Dispatcher()

# Сделать:
storage = RedisStorage.from_url(
    settings.REDIS_URL,
    state_ttl=timedelta(hours=24),   # Состояния автоистекают через 24 часа
    data_ttl=timedelta(hours=24),    # Данные FSM автоистекают через 24 часа
)
dp = Dispatcher(storage=storage)
```

3. **Добавить `REDIS_URL` в конфигурацию бота** — `telegram_bot/config.py`:

```python
REDIS_URL: str = "redis://localhost:6379/0"  # Дефолт для локальной разработки
```

4. **Обновить `.env.example`:**

```env
REDIS_URL=redis://localhost:6379/0
```

### Файлы для изменения:
- `requirements.txt` — добавить redis
- `telegram_bot/bot.py` — RedisStorage
- `telegram_bot/config.py` — REDIS_URL
- `.env.example` — REDIS_URL

---

## Критерии готовности

- [ ] Нет неиспользуемых схем и импортов
- [ ] Telegram router подключён ОДИН раз
- [ ] Naming согласован (deadline, не current_deadline)
- [ ] ВСЕ даты через `now_moscow()`, нигде нет `utcnow()`
- [ ] Все модели используют `DateTime(timezone=True)` с `default=now_moscow`
- [ ] Даты для пользователя форматируются через `format_datetime()`
- [ ] Analytics _period_start использует Moscow TZ
- [ ] Polishing workload — один GROUP BY запрос вместо N+1
- [ ] Connection pooling настроен (pool_size=10, pool_pre_ping=True)
- [ ] Индексы на все FK-колонки (миграция создана)
- [ ] Каждый сервис имеет `logger = logging.getLogger(__name__)`
- [ ] Health check проверяет соединение с БД
- [ ] Бот использует RedisStorage вместо MemoryStorage
- [ ] State TTL = 24 часа
- [ ] Все существующие тесты по-прежнему проходят
