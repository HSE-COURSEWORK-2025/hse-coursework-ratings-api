from fastapi import APIRouter
from .getData import api_v2_get_data_router


api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(api_v2_get_data_router, tags=["get_data"])
