# Edu Posts API

Минималистичный учебный backend на FastAPI. Просмотр постов открыт всем, а создание,
редактирование и удаление доступны авторизованным пользователям только для собственных
публикаций. Суперпользователь может управлять данными через SQLAdmin.

## Возможности

- регистрация и OAuth2/JWT-авторизация;
- профиль текущего пользователя;
- публичный список и просмотр постов с пагинацией;
- создание постов после входа;
- изменение и удаление только своих постов (суперпользователь может управлять всеми);
- административная панель `/admin`;
- PostgreSQL, SQLAlchemy 2, Alembic и Docker Compose;
- тестовый набор на SQLite.

## Запуск в Docker

```bash
cp .env.example .env
docker compose up --build
```

После запуска доступны:

- Swagger UI: http://localhost:8000/docs
- API: http://localhost:8000/api/v1
- админка: http://localhost:8000/admin
- проверка состояния: http://localhost:8000/health

Создание администратора в запущенном контейнере:

```bash
docker compose exec api python scripts/create_superuser.py admin admin@example.com strong-password
```

## Локальный запуск

По умолчанию без `.env` используется SQLite, поэтому PostgreSQL для быстрого знакомства
не обязателен.

```bash
cd app
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn src.main:app --reload
```

Тесты:

```bash
pytest
```

## Основные эндпоинты

| Метод | Путь | Доступ |
|---|---|---|
| POST | `/api/v1/auth/register` | любой |
| POST | `/api/v1/auth/login` | любой; form-data `username`, `password` |
| GET | `/api/v1/users/me` | по Bearer-токену |
| GET | `/api/v1/posts` | публичный |
| GET | `/api/v1/posts/{id}` | публичный |
| POST | `/api/v1/posts` | зарегистрированный пользователь |
| PATCH | `/api/v1/posts/{id}` | автор поста |
| DELETE | `/api/v1/posts/{id}` | автор поста |

Для защищённых запросов передавайте заголовок `Authorization: Bearer <token>` либо
используйте кнопку **Authorize** в Swagger UI.

