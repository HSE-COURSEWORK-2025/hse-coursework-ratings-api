from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth import get_current_user
from app.services.db.db_session import get_session
from app.services.db.schemas import RatingRecords
from app.settings import security

api_v2_ratings_router = APIRouter(prefix="/ratings", tags=["ratings"])


class RatingIn(BaseModel):
    rating: Annotated[float, Field(ge=1, le=5)]


class RatingOut(BaseModel):
    rating: float


@api_v2_ratings_router.get(
    "/my",
    response_model=RatingOut,
    status_code=status.HTTP_200_OK,
    summary="Получить текущую оценку пользователя",
)
async def get_my_rating(
    token=Depends(security),
    user_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RatingOut:
    """
    Возвращает текущую оценку (1–5) для залогиненного пользователя.
    Если пользователь ещё не голосовал, возвращает 404 Not Found.
    """
    if not user_data.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email не передан"
        )

    try:
        stmt = select(RatingRecords).where(RatingRecords.email == user_data.email)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            return RatingOut(rating=float(record.value))
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Оценка пользователя не найдена",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении оценки: {e}",
        )


@api_v2_ratings_router.post(
    "/submit",
    status_code=status.HTTP_200_OK,
    summary="Отправить или обновить оценку",
)
async def submit_rating(
    payload: RatingIn,
    token=Depends(security),
    user_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Принимает JSON {"rating": <float от 1 до 5>} и сохраняет или обновляет оценку
    для текущего пользователя.
    Если пользователь ещё не голосовал, создаётся новая запись.
    В ответ возвращается {"message": "...", "rating": <текущее значение>}.
    """
    if not user_data.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email не передан"
        )

    try:
        stmt_select = select(RatingRecords).where(
            RatingRecords.email == user_data.email
        )
        result = await session.execute(stmt_select)
        existing = result.scalar_one_or_none()

        if existing:
            stmt_update = (
                update(RatingRecords)
                .where(RatingRecords.email == user_data.email)
                .values(value=float(payload.rating))
            )
            await session.execute(stmt_update)
            message = "Оценка обновлена"
        else:
            stmt_insert = insert(RatingRecords).values(
                email=user_data.email,
                value=float(payload.rating),
            )
            await session.execute(stmt_insert)
            message = "Оценка сохранена"

        await session.commit()
        return {"message": message, "rating": float(payload.rating)}
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при сохранении оценки: {e}",
        )
