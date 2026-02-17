# Промпт 3: Исправление безопасности

## Контекст

Ты работаешь с проектом watch-service-platform — система учёта для часовой мастерской. Backend на FastAPI + SQLAlchemy 2.0 + PostgreSQL, Telegram-бот на aiogram 3.x. Перед началом работы ОБЯЗАТЕЛЬНО прочитай файл `CONVENTIONS.md` в корне проекта и `docs/TECHNICAL_SPECIFICATION.md`.

## Задача

Исправить ~10 критических проблем безопасности. Затрагивает `backend/` и `telegram_bot/`.

---

## Блок 1: Аутентификация API (CRITICAL — 3 бага)

### Что сломано

1. **ВСЕ API-эндпоинты публичны.** Нет ни одного `Depends(verify_...)`. Любой может создавать квитанции, менять сотрудников, читать аналитику.
2. **`backend/app/core/security.py`** — файл пустой.
3. **`backend/app/api/telegram.py:79-105`** — webhook принимает любой JSON без верификации. Атакующий может слать поддельные Telegram updates.

### Что сделать

1. **Реализовать `backend/app/core/security.py`:**

```python
import logging
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.core.config import settings

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str | None = Security(api_key_header)) -> str:
    """Проверка API Key для внутренних запросов от бота."""
    if not api_key or api_key != settings.API_KEY:
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key
```

2. **Добавить `API_KEY` в `backend/app/core/config.py`:**

```python
API_KEY: str  # Обязательно, без дефолта — приложение не стартует без env var
TELEGRAM_WEBHOOK_SECRET: str  # Обязательно
```

3. **Защитить ВСЕ роутеры** — в `backend/app/api/__init__.py` или в каждом роутере:

```python
from app.core.security import verify_api_key
from fastapi import Depends

# Вариант 1: на уровне роутера (предпочтительно)
router = APIRouter(
    prefix="/receipts",
    tags=["receipts"],
    dependencies=[Depends(verify_api_key)],
)
```

Применить ко ВСЕМ роутерам:
- `receipts.py`
- `employees.py`
- `operations.py`
- `returns.py`
- `polishing.py`
- `history.py`
- `notifications.py`
- `analytics.py`

4. **Защитить webhook** — в `backend/app/api/telegram.py`:

```python
from fastapi import Request, HTTPException

@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    # ... остальная обработка
```

5. **Обновить API-клиент бота** — в `telegram_bot/services/api_client.py` — передавать API Key:

```python
class APIClient:
    def __init__(self):
        self.base_url = settings.API_BASE_URL
        self.api_key = settings.API_KEY
        self.headers = {"X-API-Key": self.api_key}

    async def _request(self, method, path, **kwargs):
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                f"{self.base_url}{path}",
                headers=self.headers,
                **kwargs,
            )
```

6. **Добавить `API_KEY` в конфигурацию бота** — в `telegram_bot/config.py`.

### Файлы для изменения:
- `backend/app/core/security.py` — реализовать verify_api_key
- `backend/app/core/config.py` — добавить API_KEY, TELEGRAM_WEBHOOK_SECRET
- `backend/app/api/receipts.py` — добавить dependencies=[Depends(verify_api_key)]
- `backend/app/api/employees.py` — аналогично
- `backend/app/api/operations.py` — аналогично
- `backend/app/api/returns.py` — аналогично
- `backend/app/api/polishing.py` — аналогично
- `backend/app/api/history.py` — аналогично
- `backend/app/api/notifications.py` — аналогично
- `backend/app/api/analytics.py` — аналогично
- `backend/app/api/telegram.py` — webhook secret verification
- `telegram_bot/services/api_client.py` — передавать X-API-Key
- `telegram_bot/config.py` — добавить API_KEY

---

## Блок 2: Конфигурация (HIGH — 4 бага)

### Что сломано

1. **`backend/app/main.py:26-32`** — CORS `allow_origins=["*"]`. Любой сайт может делать запросы.
2. **`backend/app/core/config.py:14-17`** — DATABASE_URL имеет дефолт с кредами: `"postgresql://user:password@localhost/watch_service"`.
3. **`backend/app/core/config.py:24`** — TELEGRAM_BOT_TOKEN без маскировки, может попасть в логи при DEBUG.
4. **`backend/app/core/config.py:21`** — `DEBUG=True` по умолчанию, включает `echo=True` в SQLAlchemy → SQL пишется в stdout.

### Что сделать

1. **Убрать дефолтные значения для секретов** в `backend/app/core/config.py`:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Обязательные — приложение не стартует без них
    DATABASE_URL: str               # Без дефолта!
    TELEGRAM_BOT_TOKEN: str         # Без дефолта!
    API_KEY: str                    # Без дефолта!
    TELEGRAM_WEBHOOK_SECRET: str    # Без дефолта!

    # С безопасными дефолтами
    DEBUG: bool = False             # По умолчанию ВЫКЛЮЧЕН
    APP_NAME: str = "Watch Service Platform"

    class Config:
        env_file = ".env"
```

2. **Ограничить CORS** в `backend/app/main.py`:

```python
# Если API только для бота — CORS не нужен вообще.
# Если нужен — указать конкретные домены:
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

3. **Убрать echo из engine** — SQL не должен писаться в stdout даже при DEBUG:

```python
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,  # НИКОГДА не True в production
    pool_pre_ping=True,
)
```

4. **Добавить `.env.example`** в корень проекта (без реальных значений):

```env
DATABASE_URL=postgresql://user:password@localhost/watch_service
TELEGRAM_BOT_TOKEN=your-bot-token-here
API_KEY=your-api-key-here
TELEGRAM_WEBHOOK_SECRET=your-webhook-secret-here
DEBUG=false
```

5. **Убедиться что `.env` в `.gitignore`.**

### Файлы для изменения:
- `backend/app/core/config.py` — убрать дефолты секретов, DEBUG=False
- `backend/app/core/database.py` — echo=False
- `backend/app/main.py` — ограничить CORS
- `.env.example` — СОЗДАТЬ
- `.gitignore` — проверить наличие .env

---

## Блок 3: Санитизация и защита данных (MEDIUM — 3 бага)

### Что сломано

1. Пользовательский ввод (комментарии, имена) сохраняется в JSON-поля истории без санитизации.
2. Нет rate limiting — бот или внешний клиент может забить API запросами.
3. Telegram-метаданные (telegram_id, username) передаются в URL-параметрах в некоторых методах — попадают в access-логи.

### Что сделать

1. **Добавить санитизацию** в `backend/app/core/utils.py`:

```python
import re

def sanitize_text(text: str | None, max_length: int = 1000) -> str | None:
    """Очистить пользовательский ввод для безопасного хранения."""
    if text is None:
        return None
    # Удалить управляющие символы (кроме переносов строки)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    # Обрезать до max_length
    return text[:max_length].strip()
```

2. **Применить санитизацию** ко всем пользовательским текстам перед сохранением:
   - Комментарии в полировке
   - Комментарии в истории
   - Имена сотрудников
   - Payload в history events

3. **Унифицировать передачу telegram-метаданных** — ВСЕ методы api_client.py должны передавать `telegram_id` и `telegram_username` в JSON body, не в URL params:

```python
# Вместо:
await self._request("POST", f"/receipts/{id}/assign-master",
    params={"telegram_id": tid, "telegram_username": uname},
    json_data={"master_id": mid})

# Сделать:
await self._request("POST", f"/receipts/{id}/assign-master",
    json_data={"master_id": mid, "telegram_id": tid, "telegram_username": uname})
```

4. **Обновить соответствующие эндпоинты** в бэкенде для приёма telegram-метаданных из body вместо query params.

### Файлы для изменения:
- `backend/app/core/utils.py` — добавить sanitize_text
- `backend/app/services/polishing_service.py` — санитизация комментариев
- `backend/app/services/history_service.py` — санитизация payload
- `backend/app/services/employee_service.py` — санитизация имён
- `telegram_bot/services/api_client.py` — telegram_id в body
- `backend/app/api/receipts.py` — принимать telegram_id из body
- `backend/app/api/polishing.py` — аналогично

---

## Критерии готовности

- [ ] Все API-эндпоинты требуют X-API-Key (401 без него)
- [ ] Telegram webhook проверяет X-Telegram-Bot-Api-Secret-Token (403 без него)
- [ ] API-клиент бота передаёт X-API-Key в каждом запросе
- [ ] DATABASE_URL, BOT_TOKEN, API_KEY — без дефолтных значений
- [ ] DEBUG = False по умолчанию
- [ ] SQL echo отключен
- [ ] CORS ограничен (не "*")
- [ ] .env в .gitignore, есть .env.example
- [ ] Комментарии и имена проходят санитизацию
- [ ] telegram_id передаётся в JSON body, не в URL
- [ ] Все существующие тесты по-прежнему проходят
