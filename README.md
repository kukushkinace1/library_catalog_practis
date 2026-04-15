# Library Catalog API

REST API для управления библиотечным каталогом на `FastAPI` с PostgreSQL, SQLAlchemy и интеграцией с Open Library.

## Возможности

- CRUD для книг
- фильтрация и пагинация списка книг
- health check ручка
- обогащение данных книги через Open Library API
- единая обработка ошибок приложения
- асинхронная работа с БД и внешним API

## Стек

- Python 3.11
- FastAPI
- SQLAlchemy 2.0
- PostgreSQL
- Alembic
- Pydantic v2
- httpx
- Poetry

## Структура проекта

```text
src/library_catalog/
  api/                  # роутеры, схемы, зависимости FastAPI
  core/                 # конфиг, БД, логирование, обработка исключений
  data/                 # SQLAlchemy модели и репозитории
  domain/               # сервисы, мапперы, доменные исключения
  external/             # клиенты внешних API
  main.py               # точка входа FastAPI
tests/
  manual_crud_check.md  # ручной сценарий проверки API
```

## Конфигурация

Пример `.env`:

```env
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/library_catalog
API_V1_PREFIX=/api/v1
LOG_LEVEL=INFO
```

Основные настройки берутся из `src/library_catalog/core/config.py`.

## Запуск PostgreSQL

В проекте есть `docker-compose.yml` с PostgreSQL:

```powershell
docker compose up -d
docker compose ps
```

Postgres поднимается на:

- host: `127.0.0.1`
- port: `5433`
- db: `library_catalog`
- user: `postgres`
- password: `postgres`

## Установка зависимостей

```powershell
poetry install
```

## Запуск приложения

Из корня проекта:

```powershell
$env:PYTHONPATH="src"
poetry run uvicorn library_catalog.main:app --reload
```

После запуска:

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- Root: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

## API

Базовый префикс:

```text
/api/v1
```

### Health

- `GET /api/v1/health/` - проверка состояния сервиса и подключения к БД

Пример ответа:

```json
{
  "status": "healthy",
  "database": "connected"
}
```

### Books

- `POST /api/v1/books/` - создать книгу
- `GET /api/v1/books/` - получить список книг с фильтрацией и пагинацией
- `GET /api/v1/books/{book_id}` - получить книгу по ID
- `PATCH /api/v1/books/{book_id}` - частично обновить книгу
- `DELETE /api/v1/books/{book_id}` - удалить книгу

## Пример создания книги

```json
{
  "title": "Clean Code",
  "author": "Robert Martin",
  "year": 2008,
  "genre": "Programming",
  "pages": 464,
  "isbn": "9780132350884",
  "description": "A handbook of agile software craftsmanship"
}
```

## Фильтрация и пагинация

Для `GET /api/v1/books/` поддерживаются параметры:

- `title`
- `author`
- `genre`
- `year`
- `available`
- `page`
- `page_size`

Пример:

```text
/api/v1/books/?title=Clean&author=Robert&page=1&page_size=10
```

## Open Library Enrichment

При создании книги сервис пытается обогатить данные через Open Library:

- сначала поиск по `isbn`
- если не найдено, поиск по `title + author`

Если Open Library доступен и находит книгу, в поле `extra` могут попасть:

- `cover_url`
- `subjects`
- `publisher`
- `language`
- `rating`

Если внешний API недоступен или ничего не найдено, книга всё равно создаётся.

## Ошибки

В проекте используется единая обработка доменных исключений.

Типовые статусы:

- `400` - невалидные входные данные
- `404` - книга не найдена
- `409` - книга с таким ISBN уже существует
- `503` - ошибка Open Library API
- `504` - timeout Open Library API

Пример ответа:

```json
{
  "detail": "Book with ISBN '9780132350884' already exists"
}
```

## Ручная проверка CRUD

Готовый сценарий ручного тестирования лежит в файле:

[manual_crud_check.md](/abs/path/c:/PYTHON/library_catalog/tests/manual_crud_check.md)

Там есть:

- health check
- create
- get by id
- list
- filter
- update
- delete
- negative tests

## Полезные команды

Установка зависимостей:

```powershell
poetry install
```

Запуск БД:

```powershell
docker compose up -d
```

Запуск API:

```powershell
$env:PYTHONPATH="src"
poetry run uvicorn library_catalog.main:app --reload
```

Запуск тестов:

```powershell
poetry run pytest
```

## Примечания

- проект использует `src` layout, поэтому для локального запуска нужен `PYTHONPATH=src`
- если приложение не может подключиться к БД, сначала проверь `docker compose ps`
- если Open Library не отвечает, создание книги не должно падать, enrichment просто будет пропущен
