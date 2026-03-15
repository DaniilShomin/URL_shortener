# URL Shortener API

URL Shortener API - это сервис для сокращения ссылок, аналог Bitly. Построен на FastAPI с использованием PostgreSQL для хранения данных и Redis для кэширования.

## Возможности

- Создание коротких ссылок с автогенерируемым или кастомным кодом
- Перенаправление по коротким ссылкам
- Отслеживание количества кликов с Redis кэшированием
- Установка срока жизни ссылки
- API Key аутентификация для админских операций
- Health checks (liveness + readiness)
- Централизованная обработка ошибок
- Alembic миграции

## Технологии

- **FastAPI** - веб-фреймворк
- **PostgreSQL** - основная база данных
- **Redis** - кэширование и счётчик кликов
- **SQLAlchemy** - ORM
- **Pydantic** - валидация данных
- **UV** - управление зависимостями

## Быстрый старт

### Требования

- Python 3.12+
- Docker и Docker Compose

### Установка

```bash
# Клонируйте репозиторий
cd url_shortener

# Установите зависимости
make install

# Или с dev зависимостями
make dev
```

### Запуск

```bash
# Запустите PostgreSQL и Redis
make docker-up

# Запустите приложение
make run
```

### Docker

```bash
# Собрать образ
docker build -t url-shortener .

# Запустить через docker-compose
docker compose up -d
```

Приложение будет доступно по адресу: http://localhost:8000

## Использование API

> ⚠️ Операции создания, получения информации и удаления ссылок требуют `X-API-Key` заголовок

### Health Checks

```bash
# Liveness probe
curl "http://localhost:8000/health"

# Readiness probe (проверка PostgreSQL и Redis)
curl "http://localhost:8000/health/ready"
```

### Создание короткой ссылки

```bash
curl -X POST "http://localhost:8000/urls/shorten" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secure-api-key-here" \
  -d '{"original_url": "https://example.com"}'
```

Ответ:
```json
{
  "id": 1,
  "short_code": "abc12345",
  "original_url": "https://example.com",
  "click_count": 0,
  "created_at": "2024-01-01T00:00:00",
  "expires_at": null
}
```

### Создание ссылки с кастомным кодом

```bash
curl -X POST "http://localhost:8000/urls/shorten" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secure-api-key-here" \
  -d '{"original_url": "https://example.com", "custom_alias": "my-link"}'
```

### Создание ссылки со сроком жизни

```bash
curl -X POST "http://localhost:8000/urls/shorten" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secure-api-key-here" \
  -d '{"original_url": "https://example.com", "expires_at": "2026-12-31T23:59:59"}'
```

### Перенаправление по короткой ссылке

```bash
curl -L "http://localhost:8000/abc12345"
```

### Получение информации о ссылке

```bash
curl "http://localhost:8000/urls/info/abc12345" \
  -H "X-API-Key: your-secure-api-key-here"
```

### Удаление ссылки

```bash
curl -X DELETE "http://localhost:8000/urls/abc12345" \
  -H "X-API-Key: your-secure-api-key-here"
```

## Доступные команды Make

| Команда | Описание |
|---------|----------|
| `make install` | Установить зависимости |
| `make dev` | Установить с dev зависимостями |
| `make test` | Запустить тесты |
| `make lint` | Проверить код линтером |
| `make format` | Форматировать код |
| `make clean` | Очистить кэш |
| `make docker-up` | Запустить PostgreSQL и Redis |
| `make docker-down` | Остановить контейнеры |
| `make docker-logs` | Посмотреть логи контейнеров |
| `make run` | Запустить приложение |
| `make migrate` | Запустить Alembic миграции |

## Тесты

```bash
make test
```

## Переменные окружения

Создайте файл `.env` на основе примера:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/url_shortener
REDIS_URL=redis://localhost:6379/0
BASE_URL=http://localhost:8000
SHORT_CODE_LENGTH=8
MAX_CUSTOM_ALIAS_LENGTH=50
ADMIN_API_KEY=your-secure-api-key-here
CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]
```

## API документация

Интерактивная документация доступна по адресам:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
