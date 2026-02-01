# Watch Service Platform

Система учета производства и контроля качества в часовой мастерской элитных часов.

## Структура проекта

```
watch-service-platform/
│
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── main.py
│   │   ├── core/         # config, database, security
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── api/          # FastAPI routes
│   │   └── services/     # business logic
│   ├── alembic/          # migrations
│   ├── alembic.ini
│   └── requirements.txt
│
├── telegram_bot/         # Aiogram 3.x bot
│   ├── bot.py
│   ├── handlers/
│   ├── keyboards/
│   └── services/
│
├── docs/                 # Documentation
├── .env.example
└── docker-compose.yml
```

## Технологический стек

- Python 3.12
- FastAPI
- PostgreSQL
- SQLAlchemy 2.0
- Alembic
- Aiogram 3.x

## Архитектура

Backend и бот — раздельные приложения. Бот работает ТОЛЬКО через FastAPI API, прямого доступа к БД у бота нет.

## Принципы

- Event sourcing — всё события, ничего не перезаписывается
- Soft delete — ничего не удаляется
- Полная история по каждой квитанции
- Все действия логируются в HistoryEvent

## Запуск

```bash
cd backend
uvicorn app.main:app --reload
```
