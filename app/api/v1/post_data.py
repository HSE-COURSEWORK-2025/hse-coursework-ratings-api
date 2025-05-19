import json
from typing import List

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from app.services.kafka import kafka_client
from app.services.auth import get_current_user
from app.services.redis import redis_client
from app.models.models import DataItem, DataType, KafkaRawDataMsg
from app.settings import settings, security


api_v2_post_data_router = APIRouter(prefix="/post_data", tags=["post_data"])


# Ручка для отправки списка данных в Kafka с использованием BackgroundTasks
@api_v2_post_data_router.post("/raw_data/{data_type}", status_code=status.HTTP_200_OK)
async def send_google_health_connect_data_kafka(
    data: List[dict],
    data_type: DataType,
    background_tasks: BackgroundTasks,
    token=Depends(security),
    user_data=Depends(get_current_user)
):
    try:
        # Для каждого объекта из списка добавляем задачу отправки в фон
        for item in data:
            progress = item.get('progress')
            email = user_data.email
            if progress:
                payload = json.dumps({"type": "google_health_api", "progress": progress})
                await redis_client.set(
                    f"{settings.REDIS_DATA_COLLECTION_GOOGLE_HEALTH_API_PROGRESS_BAR_NAMESPACE}{email}",
                    payload,
                )

            # Подготавливаем сообщение
            data_to_send = KafkaRawDataMsg(rawData=item, dataType=data_type, userData=user_data)
            # Планируем отправку в фоне после возвращения ответа
            background_tasks.add_task(
                kafka_client.send,
                settings.RAW_DATA_KAFKA_TOPIC_NAME,
                data_to_send.model_dump()
            )
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error scheduling Kafka messages: {str(e)}"
        )



# Ручка для отправки списка данных в Kafka с использованием BackgroundTasks
@api_v2_post_data_router.post("/raw_data_google_fitness_api/{data_type}", status_code=status.HTTP_200_OK)
async def send_google_fitness_api_data_to_kafka(
    data: List[dict],
    data_type: DataType,
    background_tasks: BackgroundTasks,
    token=Depends(security),
    user_data=Depends(get_current_user)
):
    try:
        # Для каждого объекта из списка добавляем задачу отправки в фон
        for item in data:
            # Подготавливаем сообщение
            data_to_send = KafkaRawDataMsg(rawData=item, dataType=data_type, userData=user_data)
            # Планируем отправку в фоне после возвращения ответа
            background_tasks.add_task(
                kafka_client.send,
                settings.RAW_DATA_KAFKA_TOPIC_NAME,
                data_to_send.model_dump()
            )
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error scheduling Kafka messages: {str(e)}"
        )
