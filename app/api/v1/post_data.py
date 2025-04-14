import io
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from uuid import uuid4


api_v2_post_data_router = APIRouter(prefix="/post_data", tags=["post_data"])
