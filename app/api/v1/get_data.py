import json
import pandas as pd
from typing import List

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from app.services.kafka import kafka_client
from app.services.auth import get_current_user
from app.services.redis import redis_client
from app.models.models import DataItem, DataType, KafkaRawDataMsg, DataRecord, DataWithOutliers
from app.settings import settings, security
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.services.db.db_session import get_session
from app.services.db.schemas import RawRecords
from dateutil.parser import parse


api_v2_get_data_router = APIRouter(prefix="/get_data", tags=["get_data"])


# Ручка для отправки списка данных в Kafka с использованием BackgroundTasks
@api_v2_get_data_router.get("/raw_data/{data_type}", status_code=status.HTTP_200_OK)
async def get_data_type(
    data_type: DataType,
    # token=Depends(security),
    # user_data=Depends(get_current_user)
) -> List[DataRecord]:
    try:
        session: Session = await get_session().__anext__()
        stmt = select(RawRecords).where(RawRecords.data_type == data_type.value).order_by(RawRecords.time)
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
    data_type: DataType
) -> DataWithOutliers:
    try:
        z_threshold = 2
        session: Session = await get_session().__anext__()

        stmt = (
            select(RawRecords)
            .where(RawRecords.data_type == data_type.value)
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