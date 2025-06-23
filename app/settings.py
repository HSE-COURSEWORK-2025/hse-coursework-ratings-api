from pathlib import Path
import logging
import secrets
from pydantic import AnyHttpUrl, validator, EmailStr
from pydantic_settings import BaseSettings
from fastapi.security import HTTPBearer
from fastapi import WebSocket
from typing import Set
import socket
import json
import datetime

from multiprocessing import Queue
from logging.handlers import QueueHandler, QueueListener

from logging_loki import LokiHandler


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
ip = s.getsockname()[0]
s.close()


class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"
    LOG_UVICORN_FORMAT: str = "%(asctime)s %(levelname)s uvicorn: %(message)s"
    LOG_ACCESS_FORMAT: str = "%(asctime)s %(levelname)s access: %(message)s"
    LOG_DEFAULT_FORMAT: str = "%(asctime)s %(levelname)s %(name)s: %(message)s"

    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    APP_VERSION: str = "dev"
    APP_TITLE: str = "HSE-COURSEWORK Rating API"
    APP_CONTACT_NAME: str = "MALYSH_II"
    APP_CONTACT_EMAIL: EmailStr = "iimalysh@edu.hse.ru"
    APP_OPENAPI_URL: str = "/openapi.json"
    APP_DOCS_URL: str | None = "/docs"
    APP_REDOC_URL: str | None = None
    PRODUCTION: bool = False

    ROOT_PATH: str | None = "/ratings-api"
    PORT: int | None = 8080

    SECRET_KEY: str = secrets.token_urlsafe(32)

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    BACKEND_CORS_ORIGINS: list[AnyHttpUrl] = []

    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None

    GOOGLE_REDIRECT_URI: str | None = ""

    KAFKA_BOOTSTRAP_SERVERS: str | None = "localhost:9092"

    RAW_DATA_KAFKA_TOPIC_NAME: str | None = "raw_data_topic"

    DOMAIN_NAME: str | None = "http://hse-coursework-health.ru"
    AUTH_API_URL: str | None = f"{DOMAIN_NAME}:8081"
    AUTH_API_USER_INFO_PATH: str | None = "/auth-api/api/v1/auth/users/me"

    REDIS_HOST: str | None = "localhost"
    REDIS_PORT: str | None = "6379"
    REDIS_DATA_COLLECTION_GOOGLE_FITNESS_API_PROGRESS_BAR_NAMESPACE: str | None = (
        "REDIS_DATA_COLLECTION_GOOGLE_FITNESS_API_PROGRESS_BAR_NAMESPACE-"
    )
    REDIS_DATA_COLLECTION_GOOGLE_HEALTH_API_PROGRESS_BAR_NAMESPACE: str | None = (
        "REDIS_DATA_COLLECTION_GOOGLE_HEALTH_API_PROGRESS_BAR_NAMESPACE-"
    )

    REDIS_FIND_OUTLIERS_JOB_IS_ACTIVE_NAMESPACE: str | None = (
        "REDIS_FIND_OUTLIERS_JOB_IS_ACTIVE_NAMESPACE-"
    )

    BATCH_SIZE: int | None = 100

    OTLP_GRPC_ENDPOINT: str | None = "tempo:4317"
    LOKI_URL: str | None = "http://loki:3100/loki/api/v1/push"

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | list[str]) -> str | list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    class Config:
        env_file = ".env"
        # env_file = ".env.development"
        env_file_encoding = "utf-8"
        case_sensitive = False
        env_nested_delimiter = "__"
        extra = "allow"


settings = Settings()
security = HTTPBearer()
google_fitness_api_user_clients: dict[str, Set[WebSocket]] = {}
google_health_api_user_clients: dict[str, Set[WebSocket]] = {}


# def setup_logging():
#     logging.basicConfig(
#         level=settings.LOG_LEVEL.upper(),
#         format=settings.LOG_DEFAULT_FORMAT,
#     )
#     handler_default = logging.StreamHandler()
#     handler_default.setFormatter(logging.Formatter(settings.LOG_UVICORN_FORMAT))
#     logging.getLogger("uvicorn").handlers = [handler_default]
#     handler_access = logging.StreamHandler()
#     handler_access.setFormatter(logging.Formatter(settings.LOG_ACCESS_FORMAT))
#     logging.getLogger("uvicorn.access").handlers = [handler_access]




class JsonConsoleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log = {
            "timestamp"  : datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level"      : record.levelname,
            "logger"     : record.name,
            "file"       : f"{record.filename}:{record.lineno}",
            "status_code": getattr(record, "status_code", None),
            "trace_id"   : getattr(record, "otelTraceID", None),
            "span_id"    : getattr(record, "otelSpanID", None),
            "service"    : getattr(record, "otelServiceName", None),
            "msg"        : record.getMessage(),
        }
        return json.dumps(log, ensure_ascii=False)


queue = Queue(-1)
queue_handler = QueueHandler(queue)
json_formatter = JsonConsoleFormatter()

console_handler = logging.StreamHandler()
console_handler.setFormatter(json_formatter)
console_handler.setLevel(logging.INFO)


http_loki_handler = LokiHandler(
    url=settings.LOKI_URL,
    tags={"application": settings.APP_TITLE},
    auth=None,
    version="1",
)
http_loki_handler.setFormatter(json_formatter)
listener = QueueListener(queue, http_loki_handler)
listener.start()



app_logger = logging.getLogger(settings.APP_TITLE)
app_logger.setLevel(logging.INFO)
app_logger.addHandler(console_handler)
app_logger.addHandler(queue_handler)


class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return f"GET {settings.ROOT_PATH}/metrics" not in record.getMessage()

uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.addFilter(EndpointFilter())
