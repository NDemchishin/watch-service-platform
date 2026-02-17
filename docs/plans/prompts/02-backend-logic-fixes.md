# Промпт 2: Исправление логики Backend API

## Контекст

Ты работаешь с проектом watch-service-platform — система учёта для часовой мастерской. Backend на FastAPI + SQLAlchemy 2.0 + PostgreSQL. Перед началом работы ОБЯЗАТЕЛЬНО прочитай файл `CONVENTIONS.md` в корне проекта и `docs/TECHNICAL_SPECIFICATION.md` — это правила, которые нельзя нарушать.

## Задача

Исправить ~20 багов в backend логике. Все изменения касаются файлов в `backend/`.

---

## Блок 1: Транзакции (5 багов)

### Что сломано

Многошаговые бизнес-операции выполняются без единой транзакции. Если одна из частей упадёт — в БД останутся частичные данные.

1. **`backend/app/services/receipt_service.py:98,132`** — в `update_deadline`: дедлайн коммитится (`db.commit()`), затем создаются нотификации. Если создание нотификации упадёт — дедлайн изменён, а нотификация не создана.

2. **`backend/app/services/operation_service.py:73-105`** — `create`: Operation создаётся, затем employee и operation_type данные подгружаются, затем history event добавляется, потом commit. Если подгрузка данных упадёт — operation висит без истории.

3. **`backend/app/services/return_service.py:67-125`** — `create`: Return создаётся, причины привязываются, history event добавляется — 3 шага, любой сбой = частичные данные.

4. **`backend/app/services/polishing_service.py:58-104`** — `create`: PolishingDetails + history event без транзакции.

5. **`backend/app/services/notification_service.py:61-77`** — `cancel_notifications` делает UPDATE без транзакции.

### Что сделать

1. **Обновить `backend/app/core/database.py`** — `get_db()` должен управлять транзакцией:

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()    # Commit при успехе всего запроса
    except Exception:
        db.rollback()  # Rollback при любой ошибке
        raise
    finally:
        db.close()
```

2. **Во ВСЕХ сервисах** — заменить `db.commit()` на `db.flush()`:
   - `db.flush()` отправляет данные в БД (можно получить ID), но не коммитит транзакцию
   - Финальный `db.commit()` происходит в `get_db()` при успехе
   - Финальный `db.rollback()` происходит автоматически при исключении

3. **Удалить все `db.commit()` из сервисов.** Единственное место commit — `get_db()`.

4. **Удалить все `db.rollback()` из сервисов** — это тоже делает `get_db()`.

### Файлы для изменения:
- `backend/app/core/database.py` — обновить get_db()
- `backend/app/services/receipt_service.py` — flush вместо commit
- `backend/app/services/operation_service.py` — flush вместо commit
- `backend/app/services/return_service.py` — flush вместо commit
- `backend/app/services/polishing_service.py` — flush вместо commit
- `backend/app/services/notification_service.py` — flush вместо commit
- `backend/app/services/history_service.py` — flush вместо commit
- `backend/app/services/employee_service.py` — flush вместо commit

---

## Блок 2: Валидация FK и данных (6 багов)

### Что сломано

Foreign key ID принимаются без проверки существования. Даты не проверяются на логическую корректность.

1. **`backend/app/api/receipts.py:166-189`** — `update_deadline` принимает даты в прошлом.
2. **`backend/app/services/employee_service.py:59-70`** — при создании сотрудника с дублирующим `telegram_id` — crash вместо понятной ошибки (нет обработки `IntegrityError`).
3. **`backend/app/services/polishing_service.py:58-104`** — `polisher_id` не проверяется. Если передать несуществующий ID — PolishingDetails создастся с невалидным FK.
4. **`backend/app/services/operation_service.py:83-85`** — `operation_type_id` и `employee_id` не проверяются.
5. **`backend/app/services/return_service.py:93-98`** — `guilty_employee_id` и `reason_id` не проверяются.
6. **`backend/app/api/polishing.py:104-128`** — `returned_at` может быть раньше `sent_at`.

### Что сделать

1. **Создать кастомные исключения** в `backend/app/core/exceptions.py`:

```python
class AppException(Exception):
    def __init__(self, status_code: int, detail: str, error_code: str = None):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code

class NotFoundException(AppException):
    def __init__(self, resource: str, identifier):
        super().__init__(404, f"{resource} с id {identifier} не найден", "NOT_FOUND")

class ValidationException(AppException):
    def __init__(self, detail: str):
        super().__init__(400, detail, "VALIDATION_ERROR")

class DuplicateError(AppException):
    def __init__(self, detail: str):
        super().__init__(409, detail, "DUPLICATE")
```

2. **Зарегистрировать глобальный обработчик** в `backend/app/main.py`:

```python
from app.core.exceptions import AppException

@app.exception_handler(AppException)
async def app_exception_handler(request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": exc.error_code},
    )
```

3. **В каждом сервисе перед использованием FK — проверять существование:**

```python
# Пример в operation_service.py:
employee = self.db.query(Employee).get(data.employee_id)
if not employee:
    raise NotFoundException("Employee", data.employee_id)
```

4. **В receipt_service** — валидация дедлайна:
```python
from app.core.utils import now_moscow

if data.deadline and data.deadline < now_moscow():
    raise ValidationException("Дедлайн не может быть в прошлом")
```

5. **В polishing_service mark_returned** — проверка returned_at > sent_at:
```python
if data.returned_at <= polishing.sent_at:
    raise ValidationException("Дата возврата не может быть раньше даты отправки")
```

6. **В employee_service** — обработка IntegrityError:
```python
from sqlalchemy.exc import IntegrityError

try:
    self.db.add(employee)
    self.db.flush()
except IntegrityError:
    self.db.rollback()
    raise DuplicateError(f"Сотрудник с telegram_id {data.telegram_id} уже существует")
```

### Файлы для изменения:
- `backend/app/core/exceptions.py` — СОЗДАТЬ новый файл
- `backend/app/main.py` — зарегистрировать exception handler
- `backend/app/services/operation_service.py` — проверка FK
- `backend/app/services/polishing_service.py` — проверка FK + даты
- `backend/app/services/return_service.py` — проверка FK
- `backend/app/services/receipt_service.py` — валидация дедлайна
- `backend/app/services/employee_service.py` — обработка IntegrityError

---

## Блок 3: Race conditions (4 бага)

### Что сломано

Check-then-insert паттерн без блокировки. Два конкурентных запроса могут пройти проверку и оба создать запись.

1. **`backend/app/services/receipt_service.py:73-76`** — проверка `receipt_number` уникальности: `if existing: raise` → но между `if` и `insert` другой запрос может вставить ту же запись.
2. **`backend/app/services/polishing_service.py:65-68`** — аналогично для единственной записи полировки на квитанцию.
3. **`backend/app/services/polishing_service.py:114-119`** — `mark_returned`: проверка `returned_at is None`, потом установка значения. Два конкурентных запроса оба пройдут проверку.
4. **`backend/app/services/receipt_service.py:117,136-140`** — конкурентное обновление дедлайна: старые нотификации отменяются, но новые могут не создаться.

### Что сделать

1. **Заменить check-then-insert на try-except IntegrityError:**

```python
# Вместо:
existing = self.db.query(Receipt).filter(Receipt.receipt_number == number).first()
if existing:
    raise DuplicateError("...")
receipt = Receipt(receipt_number=number, ...)
self.db.add(receipt)

# Сделать:
receipt = Receipt(receipt_number=number, ...)
self.db.add(receipt)
try:
    self.db.flush()
except IntegrityError:
    self.db.rollback()
    raise DuplicateError(f"Квитанция с номером {number} уже существует")
```

2. **Для mark_returned — использовать атомарный UPDATE с условием:**

```python
from sqlalchemy import update

result = self.db.execute(
    update(PolishingDetails)
    .where(PolishingDetails.receipt_id == receipt_id)
    .where(PolishingDetails.returned_at.is_(None))  # Атомарная проверка
    .values(returned_at=now_moscow())
)
if result.rowcount == 0:
    raise ValidationException("Полировка уже возвращена или не найдена")
```

3. **Для обновления дедлайна** — обернуть cancel + create нотификаций в одну транзакцию (это уже решается Блоком 1 через get_db()).

### Файлы для изменения:
- `backend/app/services/receipt_service.py` — IntegrityError вместо check-then-insert
- `backend/app/services/polishing_service.py` — IntegrityError + атомарный UPDATE

---

## Блок 4: Пагинация (5 багов)

### Что сломано

Некоторые list-эндпоинты не поддерживают пагинацию. `total` считает возвращённые элементы, а не реальное количество в БД.

1. **`backend/app/api/operations.py:65-74`** — `/receipt/{id}` без skip/limit
2. **`backend/app/api/returns.py:65-74`** — аналогично
3. **`backend/app/services/analytics_service.py:288-315`** — `polishing_workload` грузит ВСЕ записи
4. **`backend/app/api/receipts.py:38-41`** — `total=len(receipts)` считает возвращённые записи, а не общее число
5. Несовместимость: history.py имеет пагинацию, operations.py и returns.py — нет

### Что сделать

1. **Создать единый PaginatedResponse** в `backend/app/schemas/common.py`:

```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int
```

2. **Добавить skip/limit ко ВСЕМ list-эндпоинтам:**

```python
@router.get("/receipt/{receipt_id}")
async def get_operations_by_receipt(
    receipt_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    service = OperationService(db)
    items, total = service.get_by_receipt(receipt_id, skip=skip, limit=limit)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)
```

3. **В сервисах — возвращать (items, total):**

```python
def get_by_receipt(self, receipt_id: int, skip: int = 0, limit: int = 50) -> tuple[list, int]:
    query = self.db.query(Operation).filter(Operation.receipt_id == receipt_id)
    total = query.count()
    items = query.order_by(desc(Operation.created_at)).offset(skip).limit(limit).all()
    return items, total
```

4. **Обновить receipts.py** — `total` через `query.count()`, не через `len(items)`.

### Файлы для изменения:
- `backend/app/schemas/common.py` — СОЗДАТЬ PaginatedResponse
- `backend/app/api/operations.py` — добавить skip/limit
- `backend/app/api/returns.py` — добавить skip/limit
- `backend/app/api/receipts.py` — исправить total
- `backend/app/services/operation_service.py` — возвращать (items, total)
- `backend/app/services/return_service.py` — возвращать (items, total)
- `backend/app/services/receipt_service.py` — total через count()

---

## Критерии готовности

- [ ] `get_db()` управляет транзакцией (commit/rollback)
- [ ] В сервисах нет ни одного `db.commit()` — только `db.flush()`
- [ ] Все FK проверяются на существование перед использованием
- [ ] Дедлайн в прошлом — ошибка 400
- [ ] `returned_at < sent_at` — ошибка 400
- [ ] Дублирование telegram_id — ошибка 409, а не 500
- [ ] Дублирование receipt_number — через IntegrityError, не check-then-insert
- [ ] `mark_returned` — атомарный UPDATE с условием
- [ ] Все list-эндпоинты имеют skip/limit
- [ ] `total` = реальное количество в БД
- [ ] Глобальный exception handler для AppException
- [ ] Все существующие тесты по-прежнему проходят
