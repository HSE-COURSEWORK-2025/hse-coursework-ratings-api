from fastapi import APIRouter
from .post_data import api_v2_post_data_router
from .processing_status import api_v2_processing_status_router
from .get_data import api_v2_get_data_router


api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(api_v2_post_data_router, tags=["post_data"])
api_v1_router.include_router(api_v2_processing_status_router, tags=["processing_status"])
api_v1_router.include_router(api_v2_get_data_router, tags=["get_data"])
