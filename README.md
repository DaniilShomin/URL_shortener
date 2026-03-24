# URL Shortener API

Сервис сокращения ссылок на `FastAPI` с `PostgreSQL`, `Redis` и миграциями через `Alembic`.
По умолчанию создание коротких ссылок ограничено: не более `5` запросов в минуту с одного IP.
Если `Redis` недоступен, приложение автоматически переключается на `in-memory` cache и rate limiter.
Если `PostgreSQL` недоступен, приложение в dev-режиме автоматически переключается на локальный `SQLite`.

## Полный запуск через Docker

```bash
cp .env.example .env
docker compose up -d --build
```

Поднимутся:
- API на `localhost:8000`
- `PostgreSQL` на `localhost:5432`
- `Redis` на `localhost:6379`

Проверка сервиса:

```bash
curl http://localhost:8000/health
```

## Переменные окружения

Скопируйте пример:

```bash
cp .env.example .env
```

Для контейнера приложения адреса `Postgres` и `Redis` внутри `docker-compose` уже переопределены на имена сервисов.
Параметры запуска API тоже берутся из `.env`: `APP_HOST`, `APP_PORT`, `APP_RELOAD`.
Backend-ы хранения выбираются через `.env`: `CACHE_BACKEND=redis|memory|noop`, `RATE_LIMITER_BACKEND=redis|memory`.
Для БД доступны `DATABASE_URL`, `DATABASE_FALLBACK_URL`, `DATABASE_FALLBACK_ENABLED`.

## Миграции

Применить миграции:

```bash
alembic upgrade head
```

Создать новую миграцию:

```bash
alembic revision --autogenerate -m "message"
```

При запуске через `docker compose` миграции применяются автоматически перед стартом `uvicorn`.

## Локальный запуск без Docker для API

```bash
uv run uvicorn main:app --reload
```

Инфраструктуру при этом можно поднять отдельно:

```bash
docker compose up -d postgres redis
```

Запуск без Redis тоже поддерживается:

```bash
CACHE_BACKEND=memory RATE_LIMITER_BACKEND=memory uv run uvicorn main:app --reload
```

Если не поднят и `PostgreSQL`, приложение создаст локальный файл `url_shortener.db` и продолжит работу через `SQLite`.

## Makefile

```bash
make up
make down
make logs
make build
make test
```

## Тесты

```bash
pytest -q
```
