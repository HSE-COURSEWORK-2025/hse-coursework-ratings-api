import json
import io
import qrcode
import isodate

from typing import List

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse

from dateutil.parser import parse

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.services.auth import get_current_user
from app.services.db.db_session import get_session
from app.services.db.engine import db_engine
from app.services.db.schemas import RawRecords, OutliersRecords, MLPredictionsRecords
from app.services.FHIR import FHIRTransformer
from app.models.models import DataType, DataRecord, DataWithOutliers, Prediction
from app.settings import settings, security

api_v2_get_data_router = APIRouter(prefix="/get_data", tags=["get_data"])

BATCH_SIZE = 100


@api_v2_get_data_router.get(
    "/raw_data/SleepSessionTimeData",
    status_code=status.HTTP_200_OK,
    response_model=List[DataRecord],
    summary="Получить данные с value из ISO-8601 в секундах"
)
async def get_raw_data_sleep_session_time_data(
    token=Depends(security),
    user_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
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

    try:
        stmt = (
            select(RawRecords)
            .where(
                (RawRecords.data_type == "SleepSessionTimeData") &
                (RawRecords.email == email)
            )
            .order_by(RawRecords.time)
        )
        result = await session.execute(stmt)
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


@api_v2_get_data_router.get(
    "/raw_data/{data_type}",
    status_code=status.HTTP_200_OK,
    response_model=List[DataRecord],
)
async def get_data_type(
    data_type: DataType,
    token=Depends(security),
    user_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[DataRecord]:
    """
    Возвращает данные пользователя по типу: [(timestamp, value), ...]
    """
    current_user_email = user_data.email
    if not current_user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not provided"
        )

    try:
        stmt = (
            select(RawRecords)
            .where(
                (RawRecords.data_type == data_type.value) &
                (RawRecords.email == current_user_email)
            )
            .order_by(RawRecords.time)
        )
        result = await session.execute(stmt)
        records = result.scalars().all()

        return [
            DataRecord(
                X=parse(str(rec.time)).timestamp(),
                Y=float(str(rec.value))
            )
            for rec in records
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )


@api_v2_get_data_router.get(
    "/data_with_outliers/{data_type}",
    response_model=DataWithOutliers,
    status_code=status.HTTP_200_OK,
    summary="Получить данные и заранее вычисленные выбросы (последней итерации)"
)
async def get_data_with_outliers(
    data_type: DataType,
    token=Depends(security),
    user_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DataWithOutliers:
    """
    Возвращает:
      - data: все точки (X = UNIX-время, Y = значение)
      - outliersX: список X (UNIX-времён) точек, которые считаются выбросами
        и уже сохранены в таблице OutliersRecords для последней итерации.
    """
    email = user_data.email
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email не передан"
        )

    try:
        # 1) Все данные пользователя по типу
        stmt_all = (
            select(RawRecords)
            .where(
                (RawRecords.data_type == data_type.value) &
                (RawRecords.email == email)
            )
            .order_by(RawRecords.time)
        )
        all_result = await session.execute(stmt_all)
        all_records = all_result.scalars().all()
        data = [
            DataRecord(X=rec.time.timestamp(), Y=float(rec.value))
            for rec in all_records
        ]

        # 2) Подзапрос: максимальный номер итерации выбросов
        subq = (
            select(func.max(OutliersRecords.outliers_search_iteration_num))
            .join(RawRecords, OutliersRecords.raw_record_id == RawRecords.id)
            .where(
                (RawRecords.data_type == data_type.value) &
                (RawRecords.email == email)
            )
            .scalar_subquery()
        )

        # 3) Записи, отмеченные как выбросы в этой итерации
        stmt_out = (
            select(RawRecords)
            .join(
                OutliersRecords,
                (OutliersRecords.raw_record_id == RawRecords.id) &
                (OutliersRecords.outliers_search_iteration_num == subq)
            )
            .where(
                (RawRecords.data_type == data_type.value) &
                (RawRecords.email == email)
            )
            .order_by(RawRecords.time)
        )
        out_result = await session.execute(stmt_out)
        outlier_recs = out_result.scalars().all()
        outliersX = [rec.time.timestamp() for rec in outlier_recs]

        return DataWithOutliers(data=data, outliersX=outliersX)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при выборке данных: {e}"
        )


@api_v2_get_data_router.get(
    "/predictions",
    response_model=List[Prediction],
    status_code=status.HTTP_200_OK,
    summary="Получить ML-прогнозы последней итерации"
)
async def get_predictions(
    token=Depends(security),
    user_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[Prediction]:
    """
    Возвращает список прогнозов из таблицы ml_predictions_records
    для текущего пользователя, взятых из последней итерации:
      - diagnosisName: название диагноза
      - result: вероятность (строка)
    """
    email = user_data.email
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email не передан"
        )

    try:
        # 1) Максимальный номер итерации для данного email
        subq = (
            select(func.max(MLPredictionsRecords.iteration_num))
            .where(MLPredictionsRecords.email == email)
            .scalar_subquery()
        )

        # 2) Записи этой итерации
        stmt = (
            select(MLPredictionsRecords)
            .where(
                (MLPredictionsRecords.email == email) &
                (MLPredictionsRecords.iteration_num == subq)
            )
            .order_by(MLPredictionsRecords.diagnosis_name)
        )
        recs_result = await session.execute(stmt)
        recs = recs_result.scalars().all()

        return [
            Prediction(diagnosisName=rec.diagnosis_name, result=rec.result_value)
            for rec in recs
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при выборке прогнозов: {e}"
        )


@api_v2_get_data_router.get(
    "/fhir/get_all_data",
    status_code=status.HTTP_200_OK,
    summary="Получить все данные в FHIR-формате (streaming через StreamingResponse)"
)
async def get_fhir_all_data_manual(
    email: str,
    background_tasks: BackgroundTasks
) -> StreamingResponse:
    """
    Читает из БД пачками (BATCH_SIZE) с помощью AsyncSession и
    отсылает клиенту JSON-Bundle по частям, не загружая все записи сразу.
    """
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email не передан"
        )

    # 1) Создаём AsyncSession вручную
    session: AsyncSession = db_engine.create_session()

    async def bundle_generator():
        # Отправляем начало JSON Bundle
        yield '{"resourceType":"Bundle","type":"collection","entry":['

        first = True
        last_id = 0

        while True:
            # 2) Формируем запрос для следующей пачки по id
            stmt = (
                select(RawRecords)
                .where(
                    (RawRecords.email == email) &
                    (RawRecords.id > last_id)
                )
                .order_by(RawRecords.id)
                .limit(BATCH_SIZE)
            )
            result = await session.execute(stmt)
            batch = result.scalars().all()

            if not batch:
                break

            for rec in batch:
                obs = FHIRTransformer.build_observation_dict(rec)
                if not obs:
                    continue

                entry = {
                    "fullUrl": f"urn:uuid:{rec.id}",
                    "resource": obs
                }

                if not first:
                    yield ","
                else:
                    first = False

                yield json.dumps(entry, ensure_ascii=False)
                last_id = rec.id

            # Если размер batch меньше BATCH_SIZE — это была последняя пачка
            if len(batch) < BATCH_SIZE:
                break

        # Закрываем JSON-массив и объект Bundle
        yield "]}"

    # 3) Откладываем закрытие сессии до конца стрима
    background_tasks.add_task(session.close)

    return StreamingResponse(
        bundle_generator(),
        media_type="application/fhir+json"
    )


@api_v2_get_data_router.get(
    "/fhir/get_all_data_qr",
    status_code=status.HTTP_200_OK,
    summary="Получить QR-код со ссылкой на /fhir/get_all_data для текущего пользователя"
)
async def get_fhir_all_data_qr(
    token=Depends(security),
    user_data=Depends(get_current_user)
):
    """
    Генерирует и возвращает PNG-изображение QR-кода,
    внутри которого ссылка на /get_data/fhir/get_all_data?email=<текущий_email>.
    """
    user_email = user_data.email
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email не передан"
        )

    try:
        target_url = f"{settings.DOMAIN_NAME}/get_data/fhir/get_all_data?email={user_email}"

        # Генерация QR занимает время, обёрнём в поток, чтобы не блокировать loop
        def sync_make_qr():
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(target_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()

        img_bytes = await run_in_threadpool(sync_make_qr)

        return StreamingResponse(io.BytesIO(img_bytes), media_type="image/png")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка генерации QR-кода для FHIR Bundle"
        )
