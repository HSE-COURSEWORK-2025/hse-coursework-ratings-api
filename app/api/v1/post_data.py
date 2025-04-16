import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from app.services.kafka import kafka_client
from app.services.auth import get_current_user
from app.models.models import DataItem, DataType
from typing import Annotated, List
from app.settings import settings, security
from fastapi import Depends


api_v2_post_data_router = APIRouter(prefix="/post_data", tags=["post_data"])


# Ручка для отправки списка данных в Kafka
@api_v2_post_data_router.post("/raw_data/{data_type}", status_code=status.HTTP_200_OK)
async def send_kafka(data: List[dict], data_type: DataType, token=Depends(security), user_data=Depends(get_current_user)):
    try:
        
        print('user_data',user_data)
        # # Для каждого объекта из списка отправляем сообщение в Kafka
        # for item in data:
        #     # item.dict() преобразует Pydantic модель в обычный dict
        #     await kafka_client.send(settings.RAW_DATA_KAFKA_TOPIC_NAME, item.dict())
     
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending messages to Kafka: {str(e)}"
        )
