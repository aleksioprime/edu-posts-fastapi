# Edu Posts API

Минималистичный учебный backend на FastAPI. Просмотр постов открыт всем, а создание,
редактирование и удаление доступны авторизованным пользователям только для собственных
публикаций. Суперпользователь может управлять данными через SQLAdmin.

## Возможности

- регистрация и OAuth2/JWT-авторизация;
- профиль текущего пользователя;
- публичный список и просмотр постов с пагинацией;
- необязательное изображение поста с загрузкой JPEG, PNG или WebP;
- создание постов после входа;
- изменение и удаление только своих постов (суперпользователь может управлять всеми);
- административная панель `/admin`;
- PostgreSQL, SQLAlchemy 2, Alembic и Docker Compose;
- тестовый набор на SQLite.

## Запуск в Docker

```bash
cp .env.example .env
docker compose -p edu-posts up --build -d
```

После запуска доступны:

- Swagger UI: http://localhost:8000/docs
- API: http://localhost:8000/api/v1
- админка: http://localhost:8000/admin
- проверка состояния: http://localhost:8000/health

Создание администратора в запущенном контейнере:

```bash
docker compose -p edu-posts exec api python scripts/create_superuser.py admin admin@example.com U9Utwt
```

### Служебные скрипты базы данных

Очистка удаляет всех пользователей, все посты и их изображения, но сохраняет структуру
таблиц и состояние миграций Alembic. Операция необратима и требует явного флага `--yes`:

```bash
docker compose -p edu-posts exec api python scripts/clear_database.py --yes
```

Заполнение создаёт пользователей `demo1`, `demo2`, … и тестовые посты. Из
[Lorem Picsum](https://picsum.photos/) одним запросом загружаются метаданные фотографий:
имя автора используется в заголовке, а автор, размер оригинала и ссылка на источник — в
содержимом. Для каждого нового поста загружается соответствующее изображение. Повторный
запуск не дублирует уже созданные записи:

```bash
docker compose -p edu-posts exec api python scripts/seed_database.py \
  --users 3 \
  --posts-per-user 3 \
  --password 'e4d48c'
```

Серверу требуется исходящий HTTPS-доступ к `picsum.photos`. Флаг `--without-images`
отключает загрузку файлов, но сохраняет заголовки и содержимое по метаданным фотографий.
Флаг `--local-text` использует встроенные русские тексты. Для полностью автономного
запуска передайте оба флага:

```bash
docker compose -p edu-posts exec api python scripts/seed_database.py \
  --users 3 \
  --posts-per-user 3 \
  --password 'replace-with-demo-password' \
  --without-images \
  --local-text
```

После очистки суперпользователь также удаляется, поэтому при необходимости создайте его
заново. Не используйте пароль тестовых пользователей для реальных аккаунтов.

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
| PUT | `/api/v1/posts/{id}/image` | загрузка изображения автором |
| DELETE | `/api/v1/posts/{id}/image` | удаление изображения автором |

Для защищённых запросов передавайте заголовок `Authorization: Bearer <token>` либо
используйте кнопку **Authorize** в Swagger UI.

Изображение загружается как `multipart/form-data` в поле `image`. Поддерживаются JPEG,
PNG и WebP размером до 5 МБ и не более 4096 пикселей по каждой стороне. Сервер проверяет
содержимое, преобразует файл в WebP и возвращает относительный `image_url`. Файлы доступны
публично по `/media/posts/...` и сохраняются в Docker volume `edu-posts_media_data`.

Пример загрузки после создания поста:

```bash
curl -X PUT "https://posts.aledev.ru/api/v1/posts/POST_ID/image" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -F "image=@./cover.png"
```

Отдельный `location` для `/media` в Nginx не требуется: общий reverse proxy на
`127.0.0.1:8000` передаёт запросы к изображениям в FastAPI.

## Production deployment

Workflow `.github/workflows/deploy.yml` запускается при push в `main` или вручную через
GitHub Actions. Он выполняет тесты, публикует Docker image в GHCR и обновляет приложение
в `~/edu-posts` на сервере.

### Подготовка сервера

Ниже приведён вариант для чистого сервера Ubuntu 22.04/24.04 с архитектурой `amd64`.
Workflow собирает образ для `linux/amd64`; для ARM-сервера измените параметр `platforms`
в workflow на `linux/arm64`. Команды установки основаны на официальных инструкциях
[Docker Engine для Ubuntu](https://docs.docker.com/engine/install/ubuntu/) и
[Docker Compose plugin](https://docs.docker.com/compose/install/linux/). Настройка доступа
без `sudo` описана в официальных
[post-installation steps](https://docs.docker.com/engine/install/linux-postinstall/).

1. Удалите потенциально конфликтующие пакеты, затем установите Docker Engine и Compose
plugin из официального репозитория Docker:

```bash
sudo apt remove docker.io docker-compose docker-compose-v2 docker-doc docker-buildx podman-docker containerd runc

sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker containerd

sudo docker run --rm hello-world
sudo docker compose version
```

Если конфликтующие пакеты не были установлены, `apt` может сообщить, что удалять нечего —
это нормально. Устанавливается Compose plugin, поэтому используется современная команда
`docker compose`, а не отдельная устаревшая команда `docker-compose`.

2. Создайте отдельного пользователя для деплоя и дайте ему доступ к Docker:

```bash
sudo adduser --disabled-password --gecos "" deploy
sudo usermod -aG docker deploy
sudo -u deploy mkdir -p /home/deploy/edu-posts
```

Членство в группе `docker` фактически даёт root-права на сервере. Используйте отдельного
пользователя и отдельный SSH-ключ только для CI/CD.

3. На локальной машине создайте ключ для GitHub Actions:

```bash
ssh-keygen -t ed25519 -C "github-actions-edu-posts" -f ./edu-posts-deploy
```

Содержимое `edu-posts-deploy` сохраните в GitHub secret `SERVER_SSH_KEY`. Публичную часть
`edu-posts-deploy.pub` добавьте на сервере в `/home/deploy/.ssh/authorized_keys`:

Сначала на локальной машине выведите публичный ключ и скопируйте всю строку, начинающуюся
с `ssh-ed25519`:

```bash
cat ./edu-posts-deploy.pub
```

Затем на сервере откройте файл:

```bash
sudo install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
sudoedit /home/deploy/.ssh/authorized_keys
```
Вставьте в него скопированную строку публичного ключа и сохраните файл. Не вставляйте приватный файл `edu-posts-deploy`.
После сохранения выполните:

```bash
sudo chown deploy:deploy /home/deploy/.ssh/authorized_keys
sudo chmod 600 /home/deploy/.ssh/authorized_keys
sudo wc -l /home/deploy/.ssh/authorized_keys
```

Последняя команда должна показать как минимум одну строку.

После добавления ключа проверьте вход и доступ к Docker с локальной машины:

```bash
ssh -p 22 -i ./edu-posts-deploy deploy@SERVER_HOST
docker version
docker compose version
```

4. Разрешите входящий SSH-трафик. Если API должен быть доступен напрямую, разрешите также
порт из `APP_PORT`. Для production предпочтительнее оставить API за Nginx/Caddy и открыть
наружу только `80/443`. Учитывайте, что опубликованные Docker-порты могут обходить правила
UFW; ограничения следует также настроить в firewall облачного провайдера или цепочке
`DOCKER-USER`.

Серверу нужен исходящий HTTPS-доступ к `ghcr.io`, чтобы скачивать собранный образ.

При работе за Nginx оставьте в production `.env` значение `FORWARDED_ALLOW_IPS=*`.
Production Compose публикует API только на `127.0.0.1`, поэтому forwarded-заголовки может
передать только локальный reverse proxy. Это позволяет FastAPI и SQLAdmin корректно
определять HTTPS-схему и генерировать защищённые ссылки и редиректы.

### Настройка GitHub

В GitHub Environment с именем `production` необходимо создать секреты:

- `SERVER_HOST` — адрес сервера;
- `SERVER_PORT` — SSH-порт, обычно `22`;
- `SERVER_USER` — пользователь с доступом к Docker;
- `SERVER_SSH_KEY` — приватный SSH-ключ;
- `PRODUCTION_ENV` — содержимое production-файла `.env` без `APP_IMAGE` и `IMAGE_TAG`.

Для описанной выше конфигурации `SERVER_USER` должен быть равен `deploy`. Минимальное
содержимое `PRODUCTION_ENV` можно взять из `.env.example`. Секретные значения для
`JWT_SECRET_KEY` и `ADMIN_SESSION_SECRET` можно получить отдельными запусками:

```bash
openssl rand -hex 32
```

В `PRODUCTION_ENV` не следует переносить `APP_IMAGE` и `IMAGE_TAG`: workflow добавляет
имя образа и SHA-тег автоматически перед загрузкой `.env` на сервер.

### Первый деплой и диагностика

Запустите workflow `Build and deploy` вручную через вкладку Actions или отправьте commit
в ветку `main`. После завершения проверьте состояние на сервере:

```bash
cd ~/edu-posts
docker compose -p edu-posts -f docker-compose.prod.yml ps
docker compose -p edu-posts -f docker-compose.prod.yml logs --tail=100 api
docker compose -p edu-posts -f docker-compose.prod.yml logs --tail=100 postgres
```

Служебные скрипты на сервере запускаются из каталога деплоя через production compose:

```bash
cd ~/edu-posts
docker compose -p edu-posts -f docker-compose.prod.yml exec api \
  python scripts/clear_database.py --yes
docker compose -p edu-posts -f docker-compose.prod.yml exec api \
  python scripts/seed_database.py --users 3 --posts-per-user 3 \
  --password 'replace-with-demo-password'
```

Данные PostgreSQL сохраняются в named volume `edu-posts_postgres_data`, а изображения —
в `edu-posts_media_data`. Оба volume сохраняются при обычном обновлении контейнеров. Для
production необходимо отдельно настроить резервное копирование базы данных и media volume.
