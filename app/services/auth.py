from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
import httpx
from app.models.models import TokenData
from app.settings import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    headers = {
        "Authorization": f"Bearer {token}",
        "accept": "application/json"
    }
    url = f"{settings.AUTH_API_URL}{settings.AUTH_API_USER_INFO_PATH}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    data = response.json()
    # Преобразуем полученные данные в объект модели TokenData
    user = TokenData.parse_obj(data)
    return user
