# Issues Plan / План задач

> Все задачи перечислены в порядке выполнения. Каждая issue — самостоятельная единица работы.
> Labels: `bug`, `test`, `enhancement`, `sprint-3-fix`, `sprint-4`, `sprint-5`, `sprint-6`, `infra`

---

## Фаза 1: Стабилизация Sprint 3 (багфиксы)

### Issue #1 — [bug][sprint-3-fix] Retry-логика (tenacity) импортирована, но не используется

**Файл:** `telegram_bot/services/api_client.py`

**Проблема:**
`tenacity` (retry, stop_after_attempt, wait_exponential) импортирован в строке 10, но декоратор `@retry` нигде не применяется. При любом транзиентном сетевом сбое API-клиент падает сразу.

**Что сделать:**
- Добавить `@retry` декоратор к методу `_request()` с разумными параметрами (3 попытки, exponential backoff)
- Retry только на сетевые ошибки (`httpx.ConnectError`, `httpx.TimeoutException`), НЕ на 4xx ответы

**Acceptance criteria:**
- [ ] `_request()` имеет `@retry` декоратор
- [ ] Retry срабатывает только на транзиентные ошибки
- [ ] Логируется каждая повторная попытка

---

### Issue #2 — [bug][sprint-3-fix] Дублирование обработки пагинированных ответов в API-клиенте

**Файл:** `telegram_bot/services/api_client.py`

**Проблема:**
Паттерн `response.get("items", []) if isinstance(response, dict) else response` повторяется в 5+ методах (`get_receipts`, `get_employees`, `get_all_employees`, `get_inactive_employees`, `get_return_reasons`). Это copy-paste, при изменении формата пагинации нужно будет менять в 5 местах.

**Что сделать:**
- Создать приватный метод `_unwrap_paginated(response) -> list` в `APIClient`
- Заменить все дублирования на вызов этого метода

**Acceptance criteria:**
- [ ] Один метод `_unwrap_paginated()` вместо 5 копий
- [ ] Все методы, возвращающие списки, используют его
- [ ] Поведение не изменилось (тесты проходят)

---

### Issue #3 — [bug][sprint-3-fix] Catch-all exception handling в хендлерах бота

**Файлы:** `telegram_bot/handlers/master.py`, `polishing.py`, `otk.py`, `urgent.py`

**Проблема:**
Все хендлеры используют `except Exception as e` с generic сообщением об ошибке. Это маскирует реальные проблемы: сетевые ошибки, ошибки валидации и баги API выглядят одинаково.

**Что сделать:**
- Разделить на конкретные типы: `httpx.HTTPStatusError` (4xx/5xx), `httpx.ConnectError` (сеть), `KeyError`/`ValueError` (данные)
- Для каждого типа — своё сообщение пользователю и свой уровень логирования
- Оставить финальный `except Exception` только как safety net с `logger.exception()`

**Acceptance criteria:**
- [ ] Каждый хендлер обрабатывает минимум 2 конкретных типа исключений
- [ ] Пользователь видит разные сообщения для сети vs ошибки данных
- [ ] Все ошибки логируются с полным стектрейсом (`logger.exception`)

---

### Issue #4 — [bug][sprint-3-fix] Небезопасный парсинг дат (bare except)

**Файлы:** `telegram_bot/handlers/urgent.py:42-45`, `urgent.py:91-95`, `history.py:82-85`

**Проблема:**
Парсинг ISO-дат обёрнут в голый `except:` с тихим fallback. Если API вернёт невалидную дату, пользователь увидит сырую ISO-строку без какого-либо предупреждения.

**Что сделать:**
- Заменить `except:` на `except (ValueError, TypeError):`
- Добавить `logger.warning()` при неудачном парсинге
- Вынести парсинг в утилитарную функцию `format_datetime(iso_string) -> str`

**Acceptance criteria:**
- [ ] Утилитарная функция `format_datetime()` в отдельном модуле
- [ ] Все 3 места используют эту функцию
- [ ] При невалидной дате — warning в лог + человекочитаемый fallback

---

### Issue #5 — [bug][sprint-3-fix] Непоследовательная передача параметров (query params vs JSON body)

**Файл:** `telegram_bot/services/api_client.py`

**Проблема:**
Методы `assign_to_master`, `mark_urgent`, `update_deadline` передают `telegram_id`/`telegram_username` по-разному: где-то через `params` (query), где-то через `json_data` (body). Это работает, но:
1. Пользовательские ID в URL попадают в access-логи сервера
2. Нет единообразия — трудно поддерживать

**Что сделать:**
- Определить единый стандарт: все telegram-метаданные передавать в JSON body
- Обновить соответствующие API-эндпоинты в бэкенде для приёма из body
- Обновить API-клиент

**Acceptance criteria:**
- [ ] Все методы API-клиента передают `telegram_id`/`telegram_username` одинаково
- [ ] Бэкенд-эндпоинты обновлены соответственно
- [ ] Telegram-метаданные не попадают в URL

---

### Issue #6 — [bug][sprint-3-fix] Порядок роутов в operations.py может вызвать неправильный роутинг

**Файл:** `backend/app/api/operations.py`

**Проблема:**
Роут `/types` может быть перехвачен параметризированным роутом `/{operation_id}`, если FastAPI попробует интерпретировать "types" как ID. Порядок регистрации роутов критичен.

**Что сделать:**
- Проверить порядок роутов: специфичные (`/types`, `/types/{code}`) ПЕРЕД параметризированными (`/{id}`)
- Добавить тест, подтверждающий корректный роутинг

**Acceptance criteria:**
- [ ] `/types` отвечает корректно (не 422 с "value is not a valid integer")
- [ ] `/{operation_id}` работает с числовыми ID
- [ ] Тест проверяет оба пути

---

### Issue #7 — [bug][sprint-3-fix] N+1 запрос в receipt_service.get_urgent()

**Файл:** `backend/app/services/receipt_service.py:39-69`

**Проблема:**
Для каждой квитанции с дедлайном делается отдельный запрос в `history_events` чтобы проверить, прошла ли она ОТК. При 100 квитанциях = 101 SQL-запрос.

**Что сделать:**
- Переписать на один запрос с `LEFT JOIN` + `NOT EXISTS` (или subquery)
- Убрать цикл с отдельными запросами

**Acceptance criteria:**
- [ ] Один SQL-запрос вместо N+1
- [ ] Результат идентичен предыдущей реализации
- [ ] Тест с несколькими квитанциями проверяет корректность

---

### Issue #8 — [bug][sprint-3-fix] Стаб-эндпоинты возвращают пустые списки

**Файлы:** `backend/app/api/operations.py:49-59`, `backend/app/api/returns.py:49-57`

**Проблема:**
`list_operations()` и `list_returns()` всегда возвращают `{items: [], total: 0}`. Сервисный слой не имеет метода `get_all()`.

**Что сделать:**
- Добавить `get_all()` метод в `OperationService` и `ReturnService`
- Реализовать пагинацию (skip/limit)
- Подключить эндпоинты к сервисам

**Acceptance criteria:**
- [ ] `GET /operations/` возвращает реальные данные с пагинацией
- [ ] `GET /returns/` возвращает реальные данные с пагинацией
- [ ] Тесты покрывают пустые и непустые ответы

---

## Фаза 2: Тестовое покрытие

### Issue #9 — [test][infra] Настройка тестовой инфраструктуры (pytest + fixtures)

**Проблема:**
В проекте нет ни одного теста. Нужна инфраструктура.

**Что сделать:**
- Добавить `pytest`, `pytest-asyncio`, `httpx` (для TestClient), `factory-boy` в dev-зависимости
- Создать `backend/tests/conftest.py` с:
  - Фикстура тестовой БД (SQLite in-memory или test PostgreSQL)
  - Фикстура `test_client` (FastAPI TestClient)
  - Фикстура `db_session` (для прямого доступа к сессии)
- Создать `telegram_bot/tests/conftest.py` с:
  - Мок API-клиента
  - Фикстуры для aiogram тестирования
- Создать `pytest.ini` или `pyproject.toml` секцию для pytest
- Структура:
  ```
  backend/tests/
  ├── conftest.py
  ├── test_api/
  ├── test_services/
  └── test_models/
  telegram_bot/tests/
  ├── conftest.py
  ├── test_handlers/
  └── test_api_client/
  ```

**Acceptance criteria:**
- [ ] `pytest` запускается без ошибок
- [ ] Тестовая БД создаётся и удаляется автоматически
- [ ] Минимум один dummy-тест проходит для проверки инфраструктуры

---

### Issue #10 — [test] Тесты API-эндпоинтов бэкенда: Receipts

**Файл:** `backend/app/api/receipts.py`

**Тесты:**
- `test_create_receipt` — создание квитанции, проверка 201 + поля ответа
- `test_create_receipt_duplicate_number` — дублирование номера → 400
- `test_get_receipt_by_id` — получение по ID
- `test_get_receipt_not_found` — 404 для несуществующей
- `test_get_receipt_by_number` — поиск по номеру
- `test_list_receipts_pagination` — пагинация (skip/limit)
- `test_assign_master` — назначение мастера + history event
- `test_assign_master_nonexistent_receipt` — 404
- `test_assign_master_nonexistent_employee` — 404
- `test_pass_otk` — проверка ОТК + history event
- `test_initiate_return` — инициация возврата + history event
- `test_update_deadline` — обновление дедлайна + history event
- `test_get_or_create_receipt` — создание если нет, получение если есть

**Acceptance criteria:**
- [ ] Все перечисленные тесты написаны и проходят
- [ ] Покрытие `receipts.py` > 90%

---

### Issue #11 — [test] Тесты API-эндпоинтов: Employees

**Файл:** `backend/app/api/employees.py`

**Тесты:**
- `test_create_employee`
- `test_get_employee`
- `test_list_employees` (только активные)
- `test_list_all_employees` (включая неактивных)
- `test_deactivate_employee` (soft delete)
- `test_activate_employee`
- `test_list_inactive_employees`

**Acceptance criteria:**
- [ ] Все тесты проходят
- [ ] Проверена soft-delete логика

---

### Issue #12 — [test] Тесты API-эндпоинтов: Operations

**Файл:** `backend/app/api/operations.py`

**Тесты:**
- `test_create_operation`
- `test_get_operation`
- `test_list_operations` (после исправления стаба из Issue #8)
- `test_list_operation_types`
- `test_get_operation_type_by_code`

**Acceptance criteria:**
- [ ] Все тесты проходят
- [ ] Роутинг `/types` vs `/{id}` проверен (Issue #6)

---

### Issue #13 — [test] Тесты API-эндпоинтов: Polishing

**Файл:** `backend/app/api/polishing.py`

**Тесты:**
- `test_create_polishing`
- `test_get_polishing_by_receipt`
- `test_list_in_progress`
- `test_get_by_polisher`
- `test_mark_returned`
- `test_get_stats`

**Acceptance criteria:**
- [ ] Все тесты проходят
- [ ] Статистика корректно считает day/week/month

---

### Issue #14 — [test] Тесты API-эндпоинтов: Returns

**Файл:** `backend/app/api/returns.py`

**Тесты:**
- `test_create_return_with_reasons`
- `test_create_return_with_guilty_employee`
- `test_get_return_by_id`
- `test_get_returns_by_receipt`
- `test_list_all_returns` (после Issue #8)
- `test_list_return_reasons`
- `test_get_reason_by_code`

**Acceptance criteria:**
- [ ] Все тесты проходят
- [ ] Проверены связи return → reasons → guilty_employee

---

### Issue #15 — [test] Тесты API-эндпоинтов: History

**Файл:** `backend/app/api/history.py`

**Тесты:**
- `test_get_history_by_receipt`
- `test_create_history_event`
- `test_history_event_types`
- `test_history_ordering` (хронологический порядок)

**Acceptance criteria:**
- [ ] Все тесты проходят

---

### Issue #16 — [test] Тесты сервисного слоя

**Файлы:** `backend/app/services/*.py`

**Тесты:**
- `receipt_service`: CRUD, get_urgent (после Issue #7), get_by_number
- `operation_service`: create, get_by_receipt, типы операций
- `employee_service`: CRUD, activate/deactivate, фильтрация
- `polishing_service`: create, mark_returned, get_stats, get_in_progress
- `return_service`: create с reasons, get_by_receipt
- `history_service`: create event, get_by_receipt

**Acceptance criteria:**
- [ ] Каждый сервис имеет тесты на основные операции
- [ ] N+1 запрос (Issue #7) покрыт тестом

---

### Issue #17 — [test] Тесты API-клиента бота

**Файл:** `telegram_bot/services/api_client.py`

**Тесты (с мок-сервером):**
- `test_create_receipt`
- `test_get_receipt`
- `test_assign_to_master`
- `test_get_employees` — проверка unwrap пагинации
- `test_retry_on_network_error` — после Issue #1
- `test_no_retry_on_4xx`
- `test_singleton_pattern`

**Acceptance criteria:**
- [ ] API-клиент покрыт тестами с мок-ответами
- [ ] Retry-логика протестирована
- [ ] Контракт запросов (params vs json_data) зафиксирован в тестах

---

### Issue #18 — [test] Тесты хендлеров бота (основные сценарии)

**Файлы:** `telegram_bot/handlers/*.py`

**Тесты (с мок API-клиентом):**
- `test_menu_start` — показ главного меню
- `test_master_flow` — полный цикл назначения мастера
- `test_polishing_flow` — полный цикл передачи в полировку
- `test_otk_pass` — прохождение ОТК
- `test_urgent_flow` — пометка срочного
- `test_history_view` — просмотр истории

**Acceptance criteria:**
- [ ] Основные user flows покрыты тестами
- [ ] Мок API-клиента не делает реальных запросов

---

## Фаза 3: Sprint 4 — ОТК + Возвраты (полная реализация)

### Issue #19 — [enhancement][sprint-4] Реализация полного flow возвратов: выбор причин

**Файлы:** `telegram_bot/handlers/otk.py`, `telegram_bot/states.py`

**Текущее состояние:**
Хендлер возврата — заглушка (строки 145-147: "Sprint 3 - заглушка"). FSM-состояния `OTK.select_return_reasons` и `OTK.select_responsible` определены в `states.py` (строки 38-39), но не подключены.

**Что сделать:**
1. После нажатия "Оформить возврат" → показать список причин возврата (inline-кнопки)
2. Причины загружать через `GET /returns/reasons`
3. Поддержать выбор НЕСКОЛЬКИХ причин (toggle-кнопки с галочками)
4. Кнопка "Готово" для подтверждения выбора
5. Подключить FSM-состояние `OTK.select_return_reasons`

**Acceptance criteria:**
- [ ] ОТК видит список из 6 причин возврата
- [ ] Можно выбрать несколько причин
- [ ] Выбранные причины отображаются с галочкой
- [ ] Кнопка "Готово" переводит к следующему шагу
- [ ] Тесты на хендлер

---

### Issue #20 — [enhancement][sprint-4] Атрибуция виновного при причине "полировка"

**Файлы:** `telegram_bot/handlers/otk.py`

**Требование из ТЗ:**
> Если причина = полировка → бот обязан спросить: это вина полировщика или сборщика?

**Что сделать:**
1. После выбора причин → проверить: есть ли среди них "полировка"
2. Если да → показать вопрос "Чья вина?" с вариантами: Полировщик / Сборщик
3. Загрузить список полировщиков/сборщиков для выбора конкретного виновного
4. Подключить FSM-состояние `OTK.select_responsible`

**Acceptance criteria:**
- [ ] При выборе причины "полировка" появляется доп. вопрос
- [ ] Можно выбрать виновного (полировщик или сборщик)
- [ ] Можно выбрать конкретного сотрудника
- [ ] Если "полировка" не выбрана — шаг пропускается
- [ ] Тесты

---

### Issue #21 — [enhancement][sprint-4] Создание записи Return через API (замена заглушки)

**Файлы:** `telegram_bot/handlers/otk.py`, `telegram_bot/services/api_client.py`

**Проблема:**
Сейчас `initiate_return()` вызывает `/receipts/{id}/initiate-return`, который создаёт только history event, но НЕ запись Return. Реальный эндпоинт `POST /returns/` не вызывается.

**Что сделать:**
1. Добавить метод `create_return(receipt_id, reasons, guilty_employee_id)` в API-клиент
2. В хендлере после подтверждения возврата → вызвать `POST /returns/` с выбранными причинами и виновным
3. Убрать вызов `initiate_return` (или оставить как первый шаг перед `create_return`)

**Acceptance criteria:**
- [ ] Возврат создаёт запись Return в БД (не только history event)
- [ ] Return связан с причинами и виновным (если есть)
- [ ] History event тоже создаётся
- [ ] Тесты на полный flow

---

### Issue #22 — [enhancement][sprint-4] Поддержка нескольких возвратов на одну квитанцию

**Файлы:** `telegram_bot/handlers/otk.py`

**Требование из ТЗ:**
> Возвратов может быть несколько

**Что сделать:**
1. После создания возврата → спросить "Оформить ещё один возврат?"
2. Если да → вернуться к выбору причин
3. В истории квитанции показывать все возвраты

**Acceptance criteria:**
- [ ] Можно создать 2+ возврата на одну квитанцию
- [ ] Каждый возврат — отдельная запись со своими причинами
- [ ] В истории видны все возвраты

---

### Issue #23 — [enhancement][sprint-4] Отображение возвратов в истории квитанции

**Файлы:** `telegram_bot/handlers/history.py`

**Что сделать:**
- В истории квитанции показывать возвраты с:
  - Дата
  - Причины (список)
  - Виновный (если есть)
  - Комментарий

**Acceptance criteria:**
- [ ] Возвраты видны в истории квитанции
- [ ] Причины отображаются читаемо
- [ ] Виновный сотрудник указан (если назначен)

---

## Фаза 4: Sprint 5 — Уведомления

### Issue #24 — [enhancement][sprint-5] Инфраструктура уведомлений (scheduler + модель)

**Что сделать:**
1. Добавить `APScheduler` в зависимости
2. Создать модель `Notification` (receipt_id, type, scheduled_at, sent_at, status)
3. Миграция Alembic для таблицы
4. Создать `NotificationService` с методами:
   - `schedule_notifications(receipt_id, deadline)` — при установке/изменении дедлайна
   - `cancel_notifications(receipt_id)` — при снятии дедлайна
   - `get_pending()` — получить неотправленные
5. Интегрировать scheduler в `main.py` (startup event)

**Acceptance criteria:**
- [ ] APScheduler запускается при старте приложения
- [ ] Модель Notification существует в БД
- [ ] При создании дедлайна планируются 2 уведомления
- [ ] При изменении дедлайна старые отменяются, создаются новые
- [ ] Тесты на сервис

---

### Issue #25 — [enhancement][sprint-5] Отправка уведомлений о дедлайнах в Telegram

**Что сделать:**
1. Создать список OTK-пользователей (из whitelist или конфига)
2. Реализовать отправку сообщений через Telegram Bot API:
   - В 10:00 в день сдачи: "Сегодня дедлайн по квитанции #{number}"
   - За 1 час до дедлайна: "Через 1 час дедлайн по квитанции #{number}"
3. Логировать отправку (обновлять `sent_at` в Notification)
4. Обработка ошибок: если не удалось отправить → retry

**Acceptance criteria:**
- [ ] Все OTK получают уведомление в 10:00 дня дедлайна
- [ ] Все OTK получают уведомление за 1 час
- [ ] Уведомления не дублируются (sent_at отмечен)
- [ ] При ошибке отправки — retry
- [ ] Тесты с мок-ботом

---

### Issue #26 — [enhancement][sprint-5] Уведомление при изменении дедлайна

**Что сделать:**
1. При изменении дедлайна (через бот) → отправить всем OTK:
   "Дедлайн по квитанции #{number} изменён: {old} → {new}, изменил: @{username}"
2. Перепланировать уведомления (Issue #24)

**Acceptance criteria:**
- [ ] При изменении дедлайна все OTK получают сообщение
- [ ] Старые уведомления отменены, новые запланированы
- [ ] Тесты

---

## Фаза 5: Sprint 6 — Аналитика

### Issue #27 — [enhancement][sprint-6] API аналитики: качество сборки

**Что сделать:**
1. Создать `backend/app/api/analytics.py` роутер
2. Эндпоинт `GET /analytics/quality/assembly` — качество сборки по сотрудникам:
   - Всего собрано
   - Возвраты (только по причинам: грязь, неправильная сборка, номера)
   - % качества
   - Фильтры: period (day/week/month/all), employee_id
3. Создать `AnalyticsService` с агрегационными запросами
4. Pydantic-схемы ответов

**Acceptance criteria:**
- [ ] Эндпоинт возвращает метрики качества сборки
- [ ] Фильтрация по периоду и сотруднику
- [ ] Возвраты по механизму НЕ портят качество сборки (по ТЗ)
- [ ] Тесты

---

### Issue #28 — [enhancement][sprint-6] API аналитики: качество механизма

**Что сделать:**
1. Эндпоинт `GET /analytics/quality/mechanism`:
   - Всего ремонтов механизма
   - Возвраты по причине "дефект механизма"
   - % качества
   - Фильтры: period, employee_id

**Acceptance criteria:**
- [ ] Учитываются только возвраты по механизму (по ТЗ)
- [ ] Тесты

---

### Issue #29 — [enhancement][sprint-6] API аналитики: качество полировки

**Что сделать:**
1. Эндпоинт `GET /analytics/quality/polishing`:
   - Расширение существующих polishing stats
   - Возвраты по причине "полировка" с учётом виновного
   - % качества по полировщикам
   - Фильтры: period, polisher_id

**Acceptance criteria:**
- [ ] Отдельные метрики для полировщиков
- [ ] Учитывается виновный (полировщик vs сборщик) из Issue #20
- [ ] Тесты

---

### Issue #30 — [enhancement][sprint-6] API аналитики: загрузка полировщиков

**Требование из ТЗ:**
> Система должна показывать: загрузку полировщиков, сколько часов у кого в работе

**Что сделать:**
1. Эндпоинт `GET /analytics/polishing/workload`:
   - Список полировщиков с количеством часов в работе
   - Breakdown: сложные / простые, с браслетом / без
   - Среднее время полировки

**Acceptance criteria:**
- [ ] Видна текущая загрузка каждого полировщика
- [ ] Breakdown по сложности и типу
- [ ] Тесты

---

### Issue #31 — [enhancement][sprint-6] API аналитики: производительность за период

**Что сделать:**
1. Эндпоинт `GET /analytics/performance`:
   - Операции за day/week/month по сотрудникам
   - Группировка по типу работ (сборка, механизм, полировка)
   - Общая статистика и по каждому сотруднику
2. Эндпоинт `GET /analytics/returns/summary`:
   - Возвраты за период по причинам
   - Топ-сотрудников по возвратам

**Acceptance criteria:**
- [ ] Статистика за day/week/month
- [ ] Группировка по типу работ
- [ ] Тесты

---

### Issue #32 — [enhancement][sprint-6] Отображение аналитики в боте

**Что сделать:**
1. Добавить в главное меню бота кнопку "Аналитика"
2. Подменю:
   - Качество сборки
   - Качество полировки
   - Загрузка полировщиков
   - Производительность за период
3. Форматированный вывод данных в Telegram

**Acceptance criteria:**
- [ ] Аналитика доступна из главного меню
- [ ] Данные отображаются читаемо
- [ ] Тесты на хендлеры

---

## Порядок выполнения (зависимости)

```
Фаза 1 (Sprint 3 bugfixes):
  #1 → #2 → #3 → #4 → #5 → #6 → #7 → #8
  (можно параллелить: #1-#4 независимы, #6-#8 независимы)

Фаза 2 (Тесты):
  #9 (инфраструктура) → #10-#18 (можно параллелить)

Фаза 3 (Sprint 4):
  #19 → #20 → #21 → #22 → #23
  (строгая последовательность — каждый зависит от предыдущего)

Фаза 4 (Sprint 5):
  #24 → #25 → #26
  (строгая последовательность)

Фаза 5 (Sprint 6):
  #27, #28, #29, #30 (можно параллелить) → #31 → #32
```
