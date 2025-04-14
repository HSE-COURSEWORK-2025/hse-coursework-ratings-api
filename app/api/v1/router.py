from fastapi import APIRouter
from .post_data import api_v2_post_data_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(api_v2_post_data_router, tags=["auth"])
