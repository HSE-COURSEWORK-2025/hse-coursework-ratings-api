# HSE Coursework: Ratings API

## Описание

Этот репозиторий содержит сервис для сбора и хранения пользовательских оценок. Сервис позволяет пользователям выставлять и обновлять свою оценку, а также получать свою текущую оценку. 

![](https://github.com/HSE-COURSEWORK-2025/hse-coursework-ratings-api/blob/master/swagger_demo.png)

## Основные возможности
- Получение текущей оценки пользователя
- Отправка и обновление оценки (1–5)


## Структура проекта

- `app/` — основной код приложения
  - `api/` — роутеры FastAPI
  - `services/` — бизнес-логика, работа с БД, Redis, Auth API
  - `settings.py` — глобальные настройки приложения
- `deployment/` — манифесты Kubernetes (Deployment, Service)
- `requirements.txt` — зависимости Python
- `Dockerfile` — сборка Docker-образа
- `launcher.py`, `launch_app.sh` — запуск приложения

## Быстрый старт (локально)

1. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Создайте файл `.env` или используйте `.env.development`**
3. **Запустите приложение:**
   ```bash
   python launcher.py
   ```
   или через Uvicorn:
   ```bash
   uvicorn app.main:app --reload --port 8080
   ```

## Переменные окружения

- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` — OAuth2 Google (если требуется)
- `GOOGLE_REDIRECT_URI` — URI для редиректа Google OAuth (если требуется)
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` — параметры БД
- `REDIS_HOST`, `REDIS_PORT` — параметры Redis
- `SECRET_KEY` — секрет для подписи JWT
- `ROOT_PATH`, `PORT` — путь и порт приложения
- `DOMAIN_NAME` — домен для формирования ссылок
- `AUTH_API_URL`, `AUTH_API_USER_INFO_PATH` — параметры Auth API

Пример `.env`:
```
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
ROOT_PATH=/ratings-api
PORT=8080
DB_HOST=localhost
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=ratings
REDIS_HOST=localhost
SECRET_KEY=...
AUTH_API_URL=http://localhost:8081
```

## Сборка и запуск в Docker

```bash
docker build -t awesomecosmonaut/ratings-api-app .
docker run -p 8080:8080 --env-file .env awesomecosmonaut/ratings-api-app
```

## Деплой в Kubernetes

1. Соберите и отправьте образ:
   ```bash
   ./deploy.sh
   ```
2. Остановить сервис:
   ```bash
   ./stop.sh
   ```
3. Манифесты находятся в папке `deployment/` (Deployment, Service)

## Метрики и документация
- Swagger UI: `/ratings-api/docs`
- OpenAPI: `/ratings-api/openapi.json`
- Метрики Prometheus: `/ratings-api/metrics`
