# Comprehensive Bugfix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix ~70 bugs across 4 categories: security, backend logic, infrastructure, and bot UX.

**Architecture:** Sequential execution in 4 phases. Each phase is independent and testable. Security first (foundation), then backend logic (data integrity), then infrastructure (datetime/logging/performance), finally bot UX (depends on all previous fixes).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, PostgreSQL, Aiogram 3.x, Redis, Alembic

**Key References:**
- `CONVENTIONS.md` — MANDATORY read before any code change
- `docs/TECHNICAL_SPECIFICATION.md` — product requirements
- `docs/plans/prompts/01-bot-ux-fixes.md` — detailed UX bug descriptions
- `docs/plans/prompts/02-backend-logic-fixes.md` — detailed backend bug descriptions
- `docs/plans/prompts/03-security-fixes.md` — detailed security bug descriptions
- `docs/plans/prompts/04-infrastructure-fixes.md` — detailed infrastructure bug descriptions

---

## Phase 1: Security (Tasks 1–5)

### Task 1: API Key Authentication

**Files:**
- Modify: `backend/app/core/security.py` (currently empty)
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/test_api/test_security.py`

**Step 1: Write failing test**

```python
# backend/tests/test_api/test_security.py
import pytest
from fastapi.testclient import TestClient

def test_unauthenticated_request_returns_401(test_client):
    """Request without API key should return 401."""
    response = test_client.get("/api/v1/receipts/")
    assert response.status_code == 401
    assert "Invalid or missing API key" in response.json()["detail"]

def test_authenticated_request_succeeds(test_client_with_auth):
    """Request with valid API key should succeed."""
    response = test_client_with_auth.get("/api/v1/receipts/")
    assert response.status_code == 200

def test_wrong_api_key_returns_401(test_client):
    """Request with wrong API key should return 401."""
    response = test_client.get(
        "/api/v1/receipts/",
        headers={"X-API-Key": "wrong-key"}
    )
    assert response.status_code == 401
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/nick/vscode/watch-service-platform && python -m pytest backend/tests/test_api/test_security.py -v`
Expected: FAIL — test file doesn't exist yet or security not implemented

**Step 3: Add API_KEY to config**

```python
# In backend/app/core/config.py — add to Settings class:
API_KEY: str  # No default — app won't start without it
TELEGRAM_WEBHOOK_SECRET: str  # No default
```

**Step 4: Implement verify_api_key**

```python
# backend/app/core/security.py
import logging
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.core.config import settings

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str | None = Security(api_key_header)) -> str:
    if not api_key or api_key != settings.API_KEY:
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key
```

**Step 5: Update conftest.py for auth fixtures**

Add `test_client_with_auth` fixture that includes `X-API-Key` header. Set `API_KEY=test-key` in test env.

**Step 6: Run tests to verify they pass**

Run: `cd /Users/nick/vscode/watch-service-platform && python -m pytest backend/tests/test_api/test_security.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add backend/app/core/security.py backend/app/core/config.py backend/tests/test_api/test_security.py backend/tests/conftest.py
git commit -m "feat: implement API key authentication"
```

---

### Task 2: Protect All API Routers

**Files:**
- Modify: `backend/app/api/receipts.py`
- Modify: `backend/app/api/employees.py`
- Modify: `backend/app/api/operations.py`
- Modify: `backend/app/api/returns.py`
- Modify: `backend/app/api/polishing.py`
- Modify: `backend/app/api/history.py`
- Modify: `backend/app/api/notifications.py`
- Modify: `backend/app/api/analytics.py`

**Step 1: Add `dependencies=[Depends(verify_api_key)]` to each router**

In every API file, update the `APIRouter()` creation:

```python
from fastapi import Depends
from app.core.security import verify_api_key

router = APIRouter(
    prefix="/receipts",
    tags=["receipts"],
    dependencies=[Depends(verify_api_key)],
)
```

Apply to ALL 8 router files listed above.

**Step 2: Update ALL existing test fixtures to include API key header**

In `backend/tests/conftest.py`, update `test_client` fixture to include `X-API-Key: test-key` header by default.

**Step 3: Run ALL existing tests**

Run: `cd /Users/nick/vscode/watch-service-platform && python -m pytest backend/tests/ -v`
Expected: ALL PASS (tests should use authenticated client now)

**Step 4: Commit**

```bash
git add backend/app/api/*.py backend/tests/conftest.py
git commit -m "feat: protect all API routers with API key auth"
```

---

### Task 3: Telegram Webhook Secret Verification

**Files:**
- Modify: `backend/app/api/telegram.py`
- Test: `backend/tests/test_api/test_telegram_webhook.py`

**Step 1: Write failing test**

```python
# backend/tests/test_api/test_telegram_webhook.py
def test_webhook_without_secret_returns_403(test_client_with_auth):
    response = test_client_with_auth.post(
        "/webhook/telegram/webhook",
        json={"update_id": 1}
    )
    assert response.status_code == 403

def test_webhook_with_valid_secret(test_client_with_auth):
    response = test_client_with_auth.post(
        "/webhook/telegram/webhook",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"}
    )
    # Should not be 403 (may be other error due to invalid update, but not auth error)
    assert response.status_code != 403
```

**Step 2: Run test — expect FAIL**

**Step 3: Add secret verification to webhook handler**

```python
# In backend/app/api/telegram.py — add at top of webhook handler:
secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
if secret != settings.TELEGRAM_WEBHOOK_SECRET:
    raise HTTPException(status_code=403, detail="Invalid webhook secret")
```

**Step 4: Run tests — expect PASS**

**Step 5: Commit**

```bash
git add backend/app/api/telegram.py backend/tests/test_api/test_telegram_webhook.py
git commit -m "feat: add webhook secret verification"
```

---

### Task 4: Secure Configuration (Remove Defaults, CORS, Debug)

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/core/database.py`
- Modify: `backend/app/main.py`
- Create: `.env.example`

**Step 1: Remove default values for secrets in config.py**

```python
# backend/app/core/config.py — Settings class:
DATABASE_URL: str               # No default!
TELEGRAM_BOT_TOKEN: str         # No default!
API_KEY: str                    # No default!
TELEGRAM_WEBHOOK_SECRET: str    # No default!
DEBUG: bool = False             # Default OFF
ALLOWED_ORIGINS: str = ""       # Default empty
```

**Step 2: Set echo=False in database.py**

```python
engine = create_engine(settings.DATABASE_URL, echo=False)
```

**Step 3: Restrict CORS in main.py**

```python
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Step 4: Create `.env.example`**

```env
DATABASE_URL=postgresql://user:password@localhost/watch_service
TELEGRAM_BOT_TOKEN=your-bot-token-here
API_KEY=your-api-key-here
TELEGRAM_WEBHOOK_SECRET=your-webhook-secret-here
DEBUG=false
ALLOWED_ORIGINS=
REDIS_URL=redis://localhost:6379/0
```

**Step 5: Verify `.env` is in `.gitignore`**

**Step 6: Update test conftest.py to set required env vars**

**Step 7: Run ALL tests**

Run: `cd /Users/nick/vscode/watch-service-platform && python -m pytest backend/tests/ -v`
Expected: ALL PASS

**Step 8: Commit**

```bash
git add backend/app/core/config.py backend/app/core/database.py backend/app/main.py .env.example backend/tests/conftest.py
git commit -m "fix: secure configuration — remove default secrets, restrict CORS, disable debug"
```

---

### Task 5: Update Bot API Client to Send API Key

**Files:**
- Modify: `telegram_bot/services/api_client.py`
- Modify: `telegram_bot/config.py`

**Step 1: Add API_KEY to bot config**

```python
# telegram_bot/config.py — add:
API_KEY: str = ""  # Will be set from env
```

**Step 2: Update APIClient to send X-API-Key header**

```python
# In telegram_bot/services/api_client.py — update _get_client():
self._client = httpx.AsyncClient(
    base_url=self.base_url,
    timeout=30.0,
    follow_redirects=True,
    headers={"X-API-Key": bot_config.API_KEY},
)
```

**Step 3: Run bot tests**

Run: `cd /Users/nick/vscode/watch-service-platform && python -m pytest backend/tests/test_bot/ -v`
Expected: PASS

**Step 4: Commit**

```bash
git add telegram_bot/services/api_client.py telegram_bot/config.py
git commit -m "feat: bot API client sends X-API-Key header"
```

---

## Phase 2: Backend Logic (Tasks 6–13)

### Task 6: Transaction Management in get_db()

**Files:**
- Modify: `backend/app/core/database.py`

**Step 1: Update get_db() with commit/rollback**

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

**Step 2: Run ALL tests to verify nothing breaks**

Run: `cd /Users/nick/vscode/watch-service-platform && python -m pytest backend/tests/ -v`

**Step 3: Commit**

```bash
git add backend/app/core/database.py
git commit -m "fix: add transaction management to get_db() dependency"
```

---

### Task 7: Replace db.commit() with db.flush() in ALL Services

**Files:**
- Modify: `backend/app/services/receipt_service.py`
- Modify: `backend/app/services/operation_service.py`
- Modify: `backend/app/services/return_service.py`
- Modify: `backend/app/services/polishing_service.py`
- Modify: `backend/app/services/notification_service.py`
- Modify: `backend/app/services/history_service.py`
- Modify: `backend/app/services/employee_service.py`

**Step 1: In each file, replace every `self.db.commit()` with `self.db.flush()`**

Also remove any `self.db.rollback()` calls — `get_db()` handles this now.

**Step 2: Run ALL tests**

Run: `cd /Users/nick/vscode/watch-service-platform && python -m pytest backend/tests/ -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add backend/app/services/*.py
git commit -m "fix: replace db.commit() with db.flush() in all services (transaction in get_db)"
```

---

### Task 8: Custom Exception Hierarchy + Global Handler

**Files:**
- Create: `backend/app/core/exceptions.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_api/test_exceptions.py`

**Step 1: Create exceptions.py**

```python
# backend/app/core/exceptions.py
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

**Step 2: Register handler in main.py**

```python
from app.core.exceptions import AppException
from fastapi.responses import JSONResponse

@app.exception_handler(AppException)
async def app_exception_handler(request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": exc.error_code},
    )
```

**Step 3: Write test**

```python
# backend/tests/test_api/test_exceptions.py
def test_not_found_returns_404(test_client_with_auth):
    response = test_client_with_auth.get("/api/v1/receipts/999999")
    assert response.status_code == 404
```

**Step 4: Run tests, commit**

```bash
git add backend/app/core/exceptions.py backend/app/main.py backend/tests/test_api/test_exceptions.py
git commit -m "feat: add custom exception hierarchy with global handler"
```

---

### Task 9: FK Validation in All Services

**Files:**
- Modify: `backend/app/services/operation_service.py`
- Modify: `backend/app/services/polishing_service.py`
- Modify: `backend/app/services/return_service.py`
- Modify: `backend/app/services/receipt_service.py`
- Modify: `backend/app/services/employee_service.py`

**Step 1: Add FK existence checks before every use**

In each service's `create` method, before using an FK:
```python
from app.core.exceptions import NotFoundException

employee = self.db.query(Employee).get(data.employee_id)
if not employee:
    raise NotFoundException("Employee", data.employee_id)
```

Apply to:
- `operation_service.py`: check `employee_id`, `operation_type_id`, `receipt_id`
- `polishing_service.py`: check `polisher_id`, `receipt_id`
- `return_service.py`: check `guilty_employee_id`, `reason_id`, `receipt_id`
- `receipt_service.py`: check `employee_id` in assign_master

**Step 2: Add date validation**

In `receipt_service.py` — `update_deadline`:
```python
from app.core.exceptions import ValidationException
from app.core.utils import now_moscow

if data.deadline < now_moscow():
    raise ValidationException("Дедлайн не может быть в прошлом")
```

In `polishing_service.py` — `mark_returned`:
```python
if data.returned_at <= polishing.sent_at:
    raise ValidationException("Дата возврата не может быть раньше даты отправки")
```

**Step 3: Handle IntegrityError in employee_service**

```python
from sqlalchemy.exc import IntegrityError
from app.core.exceptions import DuplicateError

try:
    self.db.add(employee)
    self.db.flush()
except IntegrityError:
    raise DuplicateError(f"Сотрудник с telegram_id {data.telegram_id} уже существует")
```

**Step 4: Run ALL tests, commit**

```bash
git add backend/app/services/*.py
git commit -m "fix: add FK validation and date checks in all services"
```

---

### Task 10: Fix Race Conditions

**Files:**
- Modify: `backend/app/services/receipt_service.py`
- Modify: `backend/app/services/polishing_service.py`

**Step 1: Replace check-then-insert with IntegrityError handling**

In `receipt_service.py` — replace the existing uniqueness check for `receipt_number` with try/except IntegrityError pattern.

In `polishing_service.py` — replace the existing single-record check with try/except IntegrityError pattern.

**Step 2: Atomic UPDATE for mark_returned**

```python
from sqlalchemy import update

result = self.db.execute(
    update(PolishingDetails)
    .where(PolishingDetails.receipt_id == receipt_id)
    .where(PolishingDetails.returned_at.is_(None))
    .values(returned_at=now_moscow())
)
if result.rowcount == 0:
    raise ValidationException("Полировка уже возвращена или не найдена")
```

**Step 3: Run tests, commit**

```bash
git add backend/app/services/receipt_service.py backend/app/services/polishing_service.py
git commit -m "fix: replace check-then-insert with atomic operations to prevent race conditions"
```

---

### Task 11: Unified Pagination

**Files:**
- Create: `backend/app/schemas/common.py`
- Modify: `backend/app/api/operations.py`
- Modify: `backend/app/api/returns.py`
- Modify: `backend/app/api/receipts.py`
- Modify: `backend/app/services/operation_service.py`
- Modify: `backend/app/services/return_service.py`
- Modify: `backend/app/services/receipt_service.py`

**Step 1: Create PaginatedResponse**

```python
# backend/app/schemas/common.py
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int
```

**Step 2: Add skip/limit to operations and returns endpoints**

**Step 3: Fix receipts total to use COUNT(*)**

**Step 4: Update services to return (items, total)**

**Step 5: Run tests, commit**

```bash
git add backend/app/schemas/common.py backend/app/api/operations.py backend/app/api/returns.py backend/app/api/receipts.py backend/app/services/*.py
git commit -m "feat: unified pagination with real total count across all list endpoints"
```

---

### Task 12: Input Sanitization

**Files:**
- Modify: `backend/app/core/utils.py` (or create if not exists)

**Step 1: Add sanitize_text function**

```python
import re

def sanitize_text(text: str | None, max_length: int = 1000) -> str | None:
    if text is None:
        return None
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text[:max_length].strip()
```

**Step 2: Apply to services that accept user text (comments, names)**

**Step 3: Run tests, commit**

```bash
git add backend/app/core/utils.py backend/app/services/*.py
git commit -m "feat: add input sanitization for user text fields"
```

---

### Task 13: Move telegram_id from URL params to JSON body

**Files:**
- Modify: `telegram_bot/services/api_client.py`
- Modify: `backend/app/api/receipts.py` (any endpoints using Query params for telegram_id)

**Step 1: Audit all api_client methods that pass telegram_id via `params`**

**Step 2: Move to `json_data` dict**

**Step 3: Update backend endpoints to read from body**

**Step 4: Run tests, commit**

```bash
git add telegram_bot/services/api_client.py backend/app/api/*.py
git commit -m "fix: move telegram_id from URL params to JSON body for privacy"
```

---

## Phase 3: Infrastructure (Tasks 14–20)

### Task 14: Moscow Timezone Helpers

**Files:**
- Create or modify: `backend/app/core/utils.py`
- Modify: `backend/app/core/config.py`

**Step 1: Add MOSCOW_TZ to config**

```python
from zoneinfo import ZoneInfo
MOSCOW_TZ = ZoneInfo("Europe/Moscow")
```

**Step 2: Create helpers in utils.py**

```python
from datetime import datetime
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

def now_moscow() -> datetime:
    return datetime.now(MOSCOW_TZ)

def format_datetime(dt: datetime) -> str:
    if dt is None:
        return "—"
    return dt.astimezone(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M")
```

**Step 3: Run tests, commit**

```bash
git add backend/app/core/utils.py backend/app/core/config.py
git commit -m "feat: add Moscow timezone helpers (now_moscow, format_datetime)"
```

---

### Task 15: Replace ALL utcnow() with now_moscow()

**Files:**
- Modify: ALL files in `backend/app/services/`
- Modify: ALL files in `backend/app/models/`

**Step 1: In all services, replace `datetime.utcnow()` with `now_moscow()`**

**Step 2: In all models, replace `server_default=sa.text('NOW()')` with `default=now_moscow`**

Also ensure `DateTime(timezone=True)` on all datetime columns.

**Step 3: Run ALL tests**

**Step 4: Commit**

```bash
git add backend/app/services/*.py backend/app/models/*.py
git commit -m "fix: replace all utcnow() with now_moscow(), use timezone-aware datetimes"
```

---

### Task 16: Fix N+1 in Analytics + Connection Pooling

**Files:**
- Modify: `backend/app/services/analytics_service.py`
- Modify: `backend/app/core/database.py`

**Step 1: Rewrite polishing_workload to single GROUP BY query**

Replace the N+1 loop with:
```python
results = (
    self.db.query(
        PolishingDetails.polisher_id,
        Employee.full_name,
        func.count(PolishingDetails.id).label("total"),
        ...
    )
    .join(Employee, Employee.id == PolishingDetails.polisher_id)
    .group_by(PolishingDetails.polisher_id, Employee.full_name)
    .all()
)
```

**Step 2: Add connection pooling to database.py**

```python
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)
```

**Step 3: Run tests, commit**

```bash
git add backend/app/services/analytics_service.py backend/app/core/database.py
git commit -m "fix: eliminate N+1 query in analytics, add connection pooling"
```

---

### Task 17: Add FK Indexes (Alembic Migration)

**Files:**
- Create: `backend/alembic/versions/003_add_fk_indexes.py`
- Modify: All model files (add `index=True` to FK columns)

**Step 1: Create migration**

```python
def upgrade():
    op.create_index('ix_operations_receipt_id', 'operations', ['receipt_id'])
    op.create_index('ix_operations_employee_id', 'operations', ['employee_id'])
    op.create_index('ix_polishing_details_receipt_id', 'polishing_details', ['receipt_id'])
    op.create_index('ix_polishing_details_polisher_id', 'polishing_details', ['polisher_id'])
    op.create_index('ix_history_events_receipt_id', 'history_events', ['receipt_id'])
    op.create_index('ix_notifications_receipt_id', 'notifications', ['receipt_id'])
    op.create_index('ix_returns_receipt_id', 'returns', ['receipt_id'])
    op.create_index('ix_receipts_receipt_number', 'receipts', ['receipt_number'])
    op.create_index('ix_employees_telegram_id', 'employees', ['telegram_id'])
```

**Step 2: Add `index=True` to model FK columns**

**Step 3: Commit**

```bash
git add backend/alembic/versions/003_add_fk_indexes.py backend/app/models/*.py
git commit -m "feat: add database indexes on all FK columns"
```

---

### Task 18: Add Logging to All Services

**Files:**
- Modify: ALL files in `backend/app/services/`

**Step 1: Add logger to each service**

```python
import logging
logger = logging.getLogger(__name__)
```

**Step 2: Add log statements to create/update/delete methods**

```python
logger.info("Creating receipt: number=%s", data.receipt_number)
logger.info("Receipt created: id=%s", receipt.id)
logger.error("Failed to create receipt: %s", str(e))
```

**Step 3: Commit**

```bash
git add backend/app/services/*.py
git commit -m "feat: add structured logging to all services"
```

---

### Task 19: Health Check with DB Verification

**Files:**
- Modify: `backend/app/main.py`

**Step 1: Update /health endpoint**

```python
from sqlalchemy import text

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "database": str(e)})
```

**Step 2: Run tests, commit**

```bash
git add backend/app/main.py
git commit -m "feat: health check verifies database connectivity"
```

---

### Task 20: Dead Code Cleanup

**Files:**
- Modify: `backend/app/schemas/polishing.py` — remove unused PolishingDetailsUpdate
- Modify: `backend/app/api/__init__.py` — fix double telegram router import
- Modify: `backend/app/schemas/receipt.py` — rename current_deadline → deadline

**Step 1: Remove PolishingDetailsUpdate from schemas/polishing.py and __init__.py**

**Step 2: Fix telegram router double import**

Check `__init__.py` and `main.py` — ensure router is included exactly once.

**Step 3: Rename current_deadline → deadline in ReceiptUpdate schema**

Update all references in `receipts.py` and `api_client.py`.

**Step 4: Run ALL tests, commit**

```bash
git add backend/app/schemas/polishing.py backend/app/api/__init__.py backend/app/schemas/receipt.py backend/app/api/receipts.py telegram_bot/services/api_client.py backend/app/schemas/__init__.py
git commit -m "fix: remove dead code, fix naming inconsistencies"
```

---

## Phase 4: Bot UX (Tasks 21–27)

### Task 21: Navigation Stack Utilities

**Files:**
- Modify: `telegram_bot/utils.py`

**Step 1: Add push_nav and pop_nav**

```python
from aiogram.fsm.context import FSMContext

async def push_nav(state: FSMContext, current_state: str, handler_name: str):
    data = await state.get_data()
    history = data.get("nav_history", [])
    history.append({"state": current_state, "handler": handler_name})
    await state.update_data(nav_history=history)

async def pop_nav(state: FSMContext) -> dict | None:
    data = await state.get_data()
    history = data.get("nav_history", [])
    if history:
        prev = history.pop()
        await state.update_data(nav_history=history)
        return prev
    return None
```

**Step 2: Commit**

```bash
git add telegram_bot/utils.py
git commit -m "feat: add navigation stack utilities (push_nav, pop_nav)"
```

---

### Task 22: Keyboard Helpers (Optional Input, Confirmation)

**Files:**
- Modify: `telegram_bot/keyboards/main_menu.py`

**Step 1: Add get_optional_input_keyboard**

```python
def get_optional_input_keyboard(field: str, back_to: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"skip:{field}")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data=f"back:{back_to}"),
         InlineKeyboardButton(text="🏠 В меню", callback_data="back:main")]
    ])
```

**Step 2: Add get_confirmation_keyboard**

```python
def get_confirmation_keyboard(action: str, item_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data=f"confirm:{action}:{item_id}"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
    ])
```

**Step 3: Commit**

```bash
git add telegram_bot/keyboards/main_menu.py
git commit -m "feat: add keyboard helpers for optional fields and confirmations"
```

---

### Task 23: Global /cancel Handler + Error Middleware

**Files:**
- Modify: `telegram_bot/handlers/menu.py`
- Modify: `telegram_bot/bot.py`

**Step 1: Add /cancel handler in menu.py**

```python
from aiogram.filters import Command, StateFilter

@router.message(Command("cancel"), StateFilter("*"))
async def cancel_handler(message: Message, state: FSMContext):
    current = await state.get_state()
    if current is None:
        await message.answer("Нет активного действия для отмены.")
        return
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=get_main_menu_keyboard())
```

**Step 2: Add error middleware in bot.py**

```python
from aiogram import BaseMiddleware

class ErrorHandlerMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception as e:
            logger.exception("Handler error: %s", e)
            state = data.get("state")
            if state:
                await state.clear()
```

**Step 3: Commit**

```bash
git add telegram_bot/handlers/menu.py telegram_bot/bot.py
git commit -m "feat: add global /cancel handler and error middleware"
```

---

### Task 24: Fix Navigation in Master + Polishing Handlers

**Files:**
- Modify: `telegram_bot/handlers/master.py`
- Modify: `telegram_bot/handlers/polishing.py`

**Step 1: Add push_nav() calls at every state transition**

**Step 2: Update back button handlers to use pop_nav()**

**Step 3: Ensure back_home_keyboard on every step**

**Step 4: Commit**

```bash
git add telegram_bot/handlers/master.py telegram_bot/handlers/polishing.py
git commit -m "fix: proper back navigation in master and polishing flows"
```

---

### Task 25: Fix Navigation in OTK + Urgent + History + Employees

**Files:**
- Modify: `telegram_bot/handlers/otk.py`
- Modify: `telegram_bot/handlers/urgent.py`
- Modify: `telegram_bot/handlers/history.py`
- Modify: `telegram_bot/handlers/employees.py`

**Step 1: Add push_nav()/pop_nav() to all handlers**

**Step 2: Fix urgent.py:53 — back from receipt detail → urgent list (not main menu)**

**Step 3: Fix employees.py — use consistent back_home_keyboard**

**Step 4: Remove state.clear() from error handlers in urgent.py:261 and history.py:299**

Instead, re-show the current step with error message.

**Step 5: Commit**

```bash
git add telegram_bot/handlers/otk.py telegram_bot/handlers/urgent.py telegram_bot/handlers/history.py telegram_bot/handlers/employees.py
git commit -m "fix: proper back navigation and error recovery in all flows"
```

---

### Task 26: Skip Buttons for Optional Fields

**Files:**
- Modify: `telegram_bot/handlers/polishing.py`
- Modify: `telegram_bot/handlers/history.py`

**Step 1: In polishing.py — replace "-" skip logic with skip button**

Show `get_optional_input_keyboard("comment", "polishing")` when asking for comment.
Add callback handler for `skip:comment` that sets `comment=None` and advances.

**Step 2: In history.py — make comment optional**

Remove "Комментарий не может быть пустым" check.
Add skip button.

**Step 3: Commit**

```bash
git add telegram_bot/handlers/polishing.py telegram_bot/handlers/history.py
git commit -m "fix: add skip buttons for optional fields, remove dash-skip antipattern"
```

---

### Task 27: Confirmation Dialogs for Destructive Actions

**Files:**
- Modify: `telegram_bot/handlers/employees.py`
- Modify: `telegram_bot/handlers/urgent.py`
- Modify: `telegram_bot/handlers/otk.py`

**Step 1: Add confirmation before employee deactivate/activate**

Show: "Деактивировать сотрудника {name}?" + [Да] [Отмена]

**Step 2: Add confirmation before deadline change**

Show: "Изменить дедлайн квитанции #{number} на {date}?" + [Да] [Отмена]

**Step 3: Fix otk.py — show employee name instead of ID in return confirmation**

**Step 4: Add callback.answer() to every callback_query handler that is missing it**

**Step 5: Run all bot tests, commit**

```bash
git add telegram_bot/handlers/employees.py telegram_bot/handlers/urgent.py telegram_bot/handlers/otk.py
git commit -m "fix: add confirmation dialogs, show names instead of IDs"
```

---

## Phase 5: Redis + Final Verification (Task 28)

### Task 28: Redis FSM Storage

**Files:**
- Modify: `requirements.txt`
- Modify: `telegram_bot/bot.py`
- Modify: `telegram_bot/config.py`

**Step 1: Add redis to requirements.txt**

**Step 2: Update bot.py to use RedisStorage**

```python
from aiogram.fsm.storage.redis import RedisStorage
from datetime import timedelta

storage = RedisStorage.from_url(
    bot_config.REDIS_URL,
    state_ttl=timedelta(hours=24),
    data_ttl=timedelta(hours=24),
)
dp = Dispatcher(storage=storage)
```

**Step 3: Add REDIS_URL to config**

```python
REDIS_URL: str = "redis://localhost:6379/0"
```

**Step 4: Run ALL tests one final time**

Run: `cd /Users/nick/vscode/watch-service-platform && python -m pytest -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add requirements.txt telegram_bot/bot.py telegram_bot/config.py
git commit -m "feat: switch bot FSM to Redis storage with 24h TTL"
```

---

## Execution Summary

| Phase | Tasks | Focus | Est. Time |
|-------|-------|-------|-----------|
| 1. Security | 1–5 | Auth, CORS, secrets | ~45 min |
| 2. Backend Logic | 6–13 | Transactions, validation, pagination | ~60 min |
| 3. Infrastructure | 14–20 | Datetime, N+1, logging, indexes | ~45 min |
| 4. Bot UX | 21–27 | Navigation, skip, confirmations | ~60 min |
| 5. Redis | 28 | FSM persistence | ~15 min |

**Total: 28 tasks, ~225 minutes**

Each task ends with a commit. Any phase can be rolled back independently.
