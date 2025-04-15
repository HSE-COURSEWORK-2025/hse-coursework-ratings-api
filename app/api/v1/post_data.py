import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from app.services.kafka import kafka_client
from app.models.models import DataItem
from typing import Annotated
from app.settings import security
from fastapi import Depends


api_v2_post_data_router = APIRouter(prefix="/post_data", tags=["post_data"])


# Ручка для отправки списка данных в Kafka
@api_v2_post_data_router.post("/send", status_code=status.HTTP_200_OK)
async def send_kafka(data: List[DataItem]):
    try:
        topic = "your_topic"  # укажите имя топика для отправки данных в Kafka

        # Для каждого объекта из списка отправляем сообщение в Kafka
        for item in data:
            # item.dict() преобразует Pydantic модель в обычный dict
            await kafka_client.send(topic, item.dict())

        return {"status": "messages sent successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending messages to Kafka: {str(e)}"
        )

# @api_v2_post_data_router.post("/send",)
# async def sendme(data: DataItem, authorization: str = Depends(security)):
#     return {"rofl": str(authorization)}


