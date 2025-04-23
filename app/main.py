import logging
import asyncio
import json
import random

from prometheus_fastapi_instrumentator import Instrumentator


from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.settings import settings, setup_logging
from app.api.root import root_router
from app.api.v1.router import api_v1_router
from app.services.db.schemas import Base
from app.services.db.engine import db_engine
from app.services.kafka import kafka_client

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security import OAuth2PasswordBearer

from app.settings import user_clients
from app.services.redis import redis_client


logger = logging.getLogger(__name__)
setup_logging()


# кастомизация для генератора openapi клиента
def custom_generate_unique_id(route: APIRoute):
    return f"{route.tags[0]}-{route.name}"

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # Здесь выполните валидацию токена (например, с помощью JWT библиотеки)
    if token != "expected_token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return token


app = FastAPI(
    root_path=settings.ROOT_PATH,
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    contact={
        "name": settings.APP_CONTACT_NAME,
        "email": str(settings.APP_CONTACT_EMAIL),
        # "url": str(settings.APP_CONTACT_URL),
    },
    generate_unique_id_function=custom_generate_unique_id,
    openapi_url=settings.APP_OPENAPI_URL,
    docs_url=settings.APP_DOCS_URL,
    redoc_url=settings.APP_REDOC_URL,
    swagger_ui_oauth2_redirect_url=settings.APP_DOCS_URL + "/oauth2-redirect",
)

instrumentator = Instrumentator(
    should_ignore_untemplated=True,
    excluded_handlers=["/metrics"],
).instrument(app)


@app.on_event("startup")
async def startup_event():
    instrumentator.expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,
        tags=["root"],
    )
    # try:
    #     Base.metadata.create_all(bind=db_engine.engine)
    # except Exception:
    #     pass

    await kafka_client.connect()
    await redis_client.connect()


@app.on_event("shutdown")
async def shutdown_event():
    # await cmdb_client_stop()
    # await FastAPILimiter.close()
    ...

    await kafka_client.disconnect()
    await redis_client.disconnect()


if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


app.include_router(api_v1_router)
app.include_router(root_router)


async def generate_random_progress():
    health = 0
    fitness = 0

    while True:
        health = min(100, health + random.randint(1, 5))
        fitness = min(100, fitness + random.randint(1, 5))

        payload = json.dumps({
            "type": "progress",
            "health": health,
            "fitness": fitness
        })

        for email in user_clients:
            await redis_client.set(f'{settings.REDIS_DATA_COLLECTION_PROGRESS_BAR_NAMESPACE}{email}', payload)

        await asyncio.sleep(1)

async def broadcast_progress():
    while True:

        # Рассылаем всем подключенным клиентам
        for email in user_clients:
            payload = await redis_client.get(f'{settings.REDIS_DATA_COLLECTION_PROGRESS_BAR_NAMESPACE}{email}')
            if payload:
                for sock in user_clients[email]:
                    try:
                        await sock.send_text(payload)
                    except Exception as e:
                        user_clients[email].discard(email)



        print('user_clients',user_clients)
        await asyncio.sleep(1)


@app.on_event("startup")
async def start_broadcast_task():
    # Запускаем бесконечный цикл, который каждую секунду будет отправлять обновления
    asyncio.create_task(generate_random_progress())
    asyncio.create_task(broadcast_progress())
    