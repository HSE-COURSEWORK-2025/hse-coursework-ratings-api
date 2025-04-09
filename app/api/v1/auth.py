import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.settings import settings
from app.services.db.schemas import User
from app.services.db.db_session import get_session

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

api_v2_auth_router = APIRouter(prefix="/auth")

# Pydantic-схемы
class GoogleAuthRequest(BaseModel):
    token: str  # для старого варианта (ID токен с клиента)

class GoogleAuthCodeRequest(BaseModel):
    code: str  # authorization code, полученный через initCodeClient на клиенте

class GoogleUser(BaseModel):
    sub: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenRefreshRequest(BaseModel):
    refresh_token: str

# Функция верификации гугловского ID токена
async def verify_google_token(token: str) -> GoogleUser:
    try:
        idinfo = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError("Invalid issuer.")
        return GoogleUser(
            sub=idinfo.get("sub"),
            email=idinfo.get("email"),
            name=idinfo.get("name"),
            picture=idinfo.get("picture"),
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

# Генерация JWT access токена нашего приложения
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

# Генерация JWT refresh токена нашего приложения
def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

# Функция для создания/обновления пользователя в БД по данным из Google
def create_or_update_user(session: Session, google_user: GoogleUser) -> User:
    db_user = session.query(User).filter(User.google_sub == google_user.sub).first()
    if not db_user:
        # Если пользователь не найден, создаём нового
        db_user = User(
            google_sub=google_user.sub,
            email=google_user.email,
            name=google_user.name,
            picture=google_user.picture,
        )
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    else:
        # Если найден, обновляем при необходимости
        updated = False
        if db_user.email != google_user.email:
            db_user.email = google_user.email
            updated = True
        if db_user.name != google_user.name:
            db_user.name = google_user.name
            updated = True
        if db_user.picture != google_user.picture:
            db_user.picture = google_user.picture
            updated = True
        if updated:
            session.commit()
            session.refresh(db_user)
    return db_user

# Эндпоинт аутентификации с использованием Google ID токена (старый вариант)
@api_v2_auth_router.post("/google", response_model=Token)
async def auth_google(request_data: GoogleAuthRequest):
    session: Session = await get_session().__anext__()

    # Верификация гугловского ID токена
    google_user = await verify_google_token(request_data.token)

    db_user = create_or_update_user(session, google_user)

    # Формирование данных для JWT нашего приложения
    token_data = {
        "google_sub": db_user.google_sub,
        "email": db_user.email,
        "name": db_user.name,
        "picture": db_user.picture,
    }
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }

# Новый эндпоинт аутентификации с использованием authorization code
@api_v2_auth_router.post("/google-code", response_model=Token)
async def auth_google_code(request_data: GoogleAuthCodeRequest):
    # 1. Обмен authorization code на токены
    token_endpoint = "https://oauth2.googleapis.com/token"
    payload = {
        "code": request_data.code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        # Для client_secret желательно использовать отдельное значение, отличное от вашего SECRET_KEY,
        # например, settings.GOOGLE_CLIENT_SECRET
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_endpoint, data=payload)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error connecting to Google token endpoint",
        )

    if token_response.status_code != 200:
        raise HTTPException(
            status_code=token_response.status_code,
            detail="Error exchanging code for tokens",
        )

    token_data = token_response.json()
    # В token_data могут быть следующие ключи: access_token, expires_in, id_token, refresh_token (если запрошен и доступен)
    id_token_value = token_data.get("id_token")
    if not id_token_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="id_token not found in token response"
        )
    
    # 2. Верификация id_token и получение данных пользователя
    google_user = await verify_google_token(id_token_value)

    # 3. Создание или обновление пользователя в БД
    session: Session = await get_session().__anext__()
    db_user = create_or_update_user(session, google_user)

    # 4. Генерация JWT токенов нашего приложения (включая access и refresh токены)
    jwt_token_data = {
        "google_sub": db_user.google_sub,
        "email": db_user.email,
        "name": db_user.name,
        "picture": db_user.picture,
    }
    access_token = create_access_token(data=jwt_token_data)
    refresh_token = create_refresh_token(data=jwt_token_data)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@api_v2_auth_router.post("/google-code-fitness", response_model=Token)
async def auth_google_code_fitness(request_data: GoogleAuthCodeRequest):
    """
    Эндпоинт для обмена authorization code на токены Google,
    предназначенные для работы с Google Fitness API.
    """
    token_endpoint = "https://oauth2.googleapis.com/token"
    payload = {
        "code": request_data.code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,  # Используйте отдельное значение для Google Client Secret
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_endpoint, data=payload)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error connecting to Google token endpoint"
        )

    if token_response.status_code != 200:
        raise HTTPException(
            status_code=token_response.status_code,
            detail="Error exchanging code for tokens"
        )

    # Распаковка ответа от Google, который должен содержать:
    # - access_token (для доступа к Google Fitness API)
    # - refresh_token (если запрошен и доступен)
    # - id_token (который можно использовать для верификации пользователя)
    token_data = token_response.json()
    
    # Если необходимо, можно дополнительно выполнить верификацию id_token и создать/обновить пользователя.
    # Например:
    id_token_value = token_data.get("id_token")
    if id_token_value:
        google_user = await verify_google_token(id_token_value)
        session: Session = await get_session().__anext__()
        create_or_update_user(session, google_user)
    
    # Возвращаем именно токены, полученные от Google.
    return {
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "token_type": "bearer",
    }


# Эндпоинт обновления токенов нашего приложения
@api_v2_auth_router.post("/refresh", response_model=Token)
async def refresh_token(refresh_req: TokenRefreshRequest):
    session: Session = await get_session().__anext__()

    try:
        payload = jwt.decode(
            refresh_req.refresh_token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        email: str = payload.get("email")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token payload invalid",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    user = session.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    token_data = {
        "google_sub": user.google_sub,
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
    }
    new_access_token = create_access_token(data=token_data)
    new_refresh_token = create_refresh_token(data=token_data)
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }

# Защищённый эндпоинт для примера
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    session: Session = await get_session().__anext__()

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("email")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = session.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

@api_v2_auth_router.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "google_sub": current_user.google_sub,
        "email": current_user.email,
        "name": current_user.name,
        "picture": current_user.picture,
    }
