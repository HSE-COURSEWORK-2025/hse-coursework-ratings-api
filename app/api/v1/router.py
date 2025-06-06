from fastapi import APIRouter
from .rating import api_v2_ratings_router


api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(api_v2_ratings_router, tags=["ratings"])
