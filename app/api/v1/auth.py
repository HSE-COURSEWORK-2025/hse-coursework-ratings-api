# main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2 import id_token
from google.auth.transport import requests
from pydantic import BaseModel
from jose import JWTError, jwt
from typing import Optional
import os
from app.settings import settings
from fastapi import APIRouter, HTTPException


# Конфигурация
# GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
# SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

api_v2_auth_router = APIRouter(prefix="/auth")


# Модели данных
class GoogleAuthRequest(BaseModel):
    token: str

class User(BaseModel):
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

# Функция для верификации Google токена
async def verify_google_token(token: str) -> User:
    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
        
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError("Invalid issuer.")
            
        return User(
            email=idinfo['email'],
            name=idinfo.get('name'),
            picture=idinfo.get('picture')
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

# Генерация JWT токена
def create_access_token(data: dict):
    to_encode = data.copy()
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

# Эндпоинт для аутентификации через Google
@api_v2_auth_router.post("/google", response_model=Token)
async def auth_google(request: GoogleAuthRequest):
    user = await verify_google_token(request.token)
    
    # Здесь должна быть логика работы с вашей БД:
    # 1. Проверка существования пользователя
    # 2. Создание нового пользователя при необходимости
    # 3. Получение/генерация внутреннего идентификатора пользователя
    
    access_token = create_access_token(
        data={"sub": user.email}  # Используйте ваш внутренний user_id
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# Защищенный эндпоинт для примера
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Здесь должна быть проверка пользователя в БД
    return {"email": email}

@api_v2_auth_router.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
