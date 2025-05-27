import json
import logging
import datetime
from typing import List

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from app.services.kafka import kafka_client
from app.services.auth import get_current_user
from app.services.redisClient import redis_client_async
from app.models.models import DataItem, DataType, KafkaRawDataMsg, ProgressPayload
from app.settings import settings, security
from dateutil import parser


api_v2_post_data_router = APIRouter(prefix="/post_data", tags=["post_data"])


@api_v2_post_data_router.post(
    "/raw_data/{data_type}",
    status_code=status.HTTP_200_OK,
    summary="Send Google Health data to Kafka and track progress in Redis",
)
async def send_google_health_connect_data_kafka(
    data: List[dict],
    data_type: DataType,
    background_tasks: BackgroundTasks,
    token=Depends(security),
    user_data=Depends(get_current_user),
):
    """
    Получает список сырых данных `data` от клиента и:
      1. Для каждого элемента планирует отправку в Kafka в фоне.
      2. Обновляет запись в Redis по email пользователя,
         если `sent_at` текущего запроса новее сохранённого.
    """
    try:
        email = user_data.email

        for item in data:
            # Формируем и планируем отправку в Kafka
            msg = KafkaRawDataMsg(
                rawData=item, dataType=data_type, userData=user_data
            ).model_dump()

            background_tasks.add_task(
                kafka_client.send, settings.RAW_DATA_KAFKA_TOPIC_NAME, msg
            )

        return {"status": "ok"}

    except Exception as e:
        logging.error(f"Error scheduling Kafka messages: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error scheduling Kafka messages",
        )


# Ручка для отправки списка данных в Kafka с использованием BackgroundTasks
@api_v2_post_data_router.post(
    "/raw_data_google_fitness_api/{data_type}", status_code=status.HTTP_200_OK
)
async def send_google_fitness_api_data_to_kafka(
    data: List[dict],
    data_type: DataType,
    background_tasks: BackgroundTasks,
    token=Depends(security),
    user_data=Depends(get_current_user),
):
    try:
        # Для каждого объекта из списка добавляем задачу отправки в фон
        for item in data:
            # Подготавливаем сообщение
            data_to_send = KafkaRawDataMsg(
                rawData=item, dataType=data_type, userData=user_data
            )
            # Планируем отправку в фоне после возвращения ответа
            background_tasks.add_task(
                kafka_client.send,
                settings.RAW_DATA_KAFKA_TOPIC_NAME,
                data_to_send.model_dump(),
            )
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error scheduling Kafka messages: {str(e)}",
        )


@api_v2_post_data_router.post(
    "/progress",
    status_code=status.HTTP_200_OK,
    summary="Обновить прогресс-бар для пользователя",
)
async def update_progress_async(
    payload: ProgressPayload,
    # Если нужно ограничить доступ этим роутом, раскомментируйте:
    # token = Depends(security),
    # user_data = Depends(get_current_user)
):
    """
    Синхронный роут. Записывает в Redis для заданного email:
      {
        "type": "google_health_api",
        "progress": <0–100>
      }
    """
    try:
        redis_key = (
            f"{settings.REDIS_DATA_COLLECTION_GOOGLE_HEALTH_API_PROGRESS_BAR_NAMESPACE}"
            f"{payload.email}"
        )

        record = {
            "type": "google_health_api",
            "progress": payload.progress,
            "sent_at": datetime.datetime.utcnow().isoformat() + "Z",
        }

        await redis_client_async.set(redis_key, json.dumps(record))

        return {"status": "progress updated", "record": record}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cannot update progress: {e}",
        )
