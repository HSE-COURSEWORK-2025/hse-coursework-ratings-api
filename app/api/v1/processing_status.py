import json
from typing import List
import random
import asyncio
from fastapi import (
    APIRouter,
    HTTPException,
    status,
    BackgroundTasks,
    Depends,
    WebSocket,
    WebSocketDisconnect,
)
from app.services.kafka import kafka_client
from app.services.auth import get_current_user
from app.models.models import DataItem, DataType, KafkaRawDataMsg
from app.settings import settings, security, google_fitness_api_user_clients, google_health_api_user_clients


api_v2_processing_status_router = APIRouter(
    prefix="/processing_status", tags=["processing_status"]
)


@api_v2_processing_status_router.websocket("/google_fitness_api_progress")
async def google_fitness_api_progress_websocket_endpoint(
    websocket: WebSocket, token: str
):
    await websocket.accept()
    user_data = await get_current_user(token)
    user_email = user_data.email

    google_fitness_api_user_clients.setdefault(user_email, set()).add(websocket)

    try:
        while True:
            data = await websocket.receive_text()

    except WebSocketDisconnect:
        print(f"Client {user_email} disconnected")
    finally:
        google_fitness_api_user_clients[user_email].discard(websocket)


@api_v2_processing_status_router.websocket("/google_health_api_progress")
async def google_health_api_progress_websocket_endpoint(
    websocket: WebSocket, token: str
):
    await websocket.accept()
    user_data = await get_current_user(token)
    user_email = user_data.email

    google_health_api_user_clients.setdefault(user_email, set()).add(websocket)

    try:
        while True:
            data = await websocket.receive_text()

    except WebSocketDisconnect:
        print(f"Client {user_email} disconnected")
    finally:
        google_fitness_api_user_clients[user_email].discard(websocket)
