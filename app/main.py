import logging
import asyncio

from prometheus_fastapi_instrumentator import Instrumentator


from fastapi import FastAPI, Request
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware

from app.settings import settings, app_logger
from app.api.root import root_router
from app.api.v1.router import api_v1_router

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.settings import google_fitness_api_user_clients, google_health_api_user_clients
from app.services.redisClient import redis_client_async

from app.services.utils import PrometheusMiddleware, metrics, setting_otlp



logger = logging.getLogger(__name__)

def custom_generate_unique_id(route: APIRoute):
    return f"{route.tags[0]}-{route.name}"


security = HTTPBearer()


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
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
    },
    generate_unique_id_function=custom_generate_unique_id,
    openapi_url=settings.APP_OPENAPI_URL,
    docs_url=settings.APP_DOCS_URL,
    redoc_url=settings.APP_REDOC_URL,
    swagger_ui_oauth2_redirect_url=settings.APP_DOCS_URL + "/oauth2-redirect",
)
app.add_middleware(PrometheusMiddleware, app_name=settings.APP_TITLE)
app.add_route("/metrics", metrics)
setting_otlp(app, settings.APP_TITLE, settings.OTLP_GRPC_ENDPOINT)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    status = response.status_code
    app_logger.info(
        f"{request.method} {request.url.path}",
        extra={"status_code": status}
    )
    return response


# instrumentator = Instrumentator(
#     should_ignore_untemplated=True,
#     excluded_handlers=["/metrics"],
# ).instrument(app)


@app.on_event("startup")
async def startup_event():
    # instrumentator.expose(
    #     app,
    #     endpoint="/metrics",
    #     include_in_schema=False,
    #     tags=["root"],
    # )

    await redis_client_async.connect()


@app.on_event("shutdown")
async def shutdown_event():

    await redis_client_async.disconnect()


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


async def broadcast_fitness_api_progress():
    while True:
        for email in google_fitness_api_user_clients:
            google_fitness_api_payload = await redis_client_async.get(
                f"{settings.REDIS_DATA_COLLECTION_GOOGLE_FITNESS_API_PROGRESS_BAR_NAMESPACE}{email}"
            )

            if google_fitness_api_payload:
                for sock in google_fitness_api_user_clients[email]:
                    try:
                        await sock.send_text(google_fitness_api_payload)
                    except Exception:
                        google_fitness_api_user_clients[email].discard(email)

        await asyncio.sleep(1)


async def broadcast_health_api_progress():
    while True:
        for email in google_health_api_user_clients:
            google_health_api_payload = await redis_client_async.get(
                f"{settings.REDIS_DATA_COLLECTION_GOOGLE_HEALTH_API_PROGRESS_BAR_NAMESPACE}{email}"
            )

            if google_health_api_payload:
                for sock in google_health_api_user_clients[email]:
                    try:
                        await sock.send_text(google_health_api_payload)
                    except Exception:
                        google_health_api_user_clients[email].discard(email)

        await asyncio.sleep(1)


@app.on_event("startup")
async def start_broadcast_task():
    asyncio.create_task(broadcast_fitness_api_progress())
    asyncio.create_task(broadcast_health_api_progress())
