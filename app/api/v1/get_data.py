import json
import pandas as pd
import isodate
from typing import List

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from app.services.kafka import kafka_client
from app.services.auth import get_current_user
from app.services.redisClient import redis_client_async
from app.models.models import DataItem, DataType, KafkaRawDataMsg, DataRecord, DataWithOutliers, Prediction
from app.settings import settings, security
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.services.db.db_session import get_session
from app.services.db.schemas import RawRecords
from dateutil.parser import parse


api_v2_get_data_router = APIRouter(prefix="/get_data", tags=["get_data"])


@api_v2_get_data_router.get(
    "/raw_data/SleepSessionTimeData",
    status_code=status.HTTP_200_OK,
    response_model=List[DataRecord],
    summary="Получить данные с value из ISO-8601 в секундах"
)
async def get_raw_data_sleep_session_time_data(
    token=Depends(security),
    user_data=Depends(get_current_user)
) -> List[DataRecord]:
    """
    Возвращает список точек:
      - X = UNIX-время из поля `time` (с учётом таймзоны)
      - Y = длительность в секундах, разобранная из строки `value` (ISO-8601, например PT1H10M)
    """
    email = user_data.email
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email не передан"
        )

    # Открываем сессию
    session: Session = await get_session().__anext__()
    try:
        stmt = (
            select(RawRecords)
            .where(
                (RawRecords.data_type == "SleepSessionTimeData") &
                (RawRecords.email == email)
            )
            .order_by(RawRecords.time)
        )
        result = session.execute(stmt)
        records = result.scalars().all()

        output: List[DataRecord] = []
        for rec in records:
            # X: timestamp из datetime с tzinfo
            try:
                x = rec.time.timestamp()
            except Exception:
                continue  # пропускаем некорректные записи

            # Y: парсим ISO-8601 строку в секунды
            try:
                duration = isodate.parse_duration(rec.value)
                if hasattr(duration, "total_seconds"):
                    total_seconds = duration.total_seconds()
                else:
                    total_seconds = (
                        (duration.days or 0) * 86400 +
                        # (duration.hours or 0) * 3600 +
                        # (duration.minutes or 0) * 60 +
                        (duration.seconds or 0)
                    )
            except Exception:
                continue  # пропускаем, если формат невалиден

            output.append(DataRecord(X=x, Y=float(total_seconds)))

        return output

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при выборке данных: {e}"
        )
    finally:
        session.close()


# Ручка для отправки списка данных в Kafka с использованием BackgroundTasks
@api_v2_get_data_router.get("/raw_data/{data_type}", status_code=status.HTTP_200_OK)
async def get_data_type(
    data_type: DataType,
    token=Depends(security),
    user_data=Depends(get_current_user)
) -> List[DataRecord]:
    try:
        current_user_email = user_data.email

        if not current_user_email:
            raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email not provided"
        )

        session: Session = await get_session().__anext__()
        stmt = (
            select(RawRecords)
            .where(
                (RawRecords.data_type == data_type.value)
                & (RawRecords.email == current_user_email)
            )
            .order_by(RawRecords.time)
        )
        result = session.execute(stmt)
        records = result.scalars().all()

        result = [DataRecord(X=parse(str(rec.time)).timestamp(), Y=float(str(rec.value))) for rec in records]
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )


@api_v2_get_data_router.get(
    "/data_with_outliers/{data_type}",
    response_model=DataWithOutliers,
    status_code=status.HTTP_200_OK,
)
async def get_data_with_outliers(
    data_type: DataType,
    token=Depends(security),
    user_data=Depends(get_current_user)
) -> DataWithOutliers:
    
    current_user_email = user_data.email

    if not current_user_email:
        raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Email not provided"
    )

    try:
        z_threshold = 2
        session: Session = await get_session().__anext__()

        stmt = (
            select(RawRecords)
            .where(
                (RawRecords.data_type == data_type.value)
                & (RawRecords.email == current_user_email)
            )
            .order_by(RawRecords.time)
        )
        result = session.execute(stmt)
        records = result.scalars().all()

        rec_list = [
            DataRecord(
                X=parse(str(rec.time)).timestamp(),
                Y=float(str(rec.value))
            )
            for rec in records
        ]

        df = pd.DataFrame([{"x": r.X, "y": r.Y} for r in rec_list])

        # Z-score метод
        mean_y = df["y"].mean()
        std_y  = df["y"].std(ddof=0)  # population std
        # маска: |y - mean| > threshold * std
        mask_outliers = (df["y"] - mean_y).abs() > z_threshold * std_y
        outliers_x = df.loc[mask_outliers, "x"].tolist()

        return DataWithOutliers(
            data=rec_list,
            outliersX=outliers_x
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching or processing data: {e}"
        )


@api_v2_get_data_router.get(
    "/predictions",
    response_model=List[Prediction],
    status_code=status.HTTP_200_OK,
)
async def get_predictions(
    data_type: DataType,
    # token=Depends(security),
    # user_data=Depends(get_current_user)
) -> List[Prediction]:
    try:
        
        return []

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching or processing data: {e}"
        )
