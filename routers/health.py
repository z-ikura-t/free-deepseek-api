from fastapi import APIRouter, status, Depends

from .deps import get_ds_session
from curl_cffi.requests import AsyncSession

import models

from src.health import check_health

health_router = APIRouter(tags=['Health'])



@health_router.get('/api/health')
async def health(ds_session: AsyncSession = Depends(get_ds_session)) -> models.HealthModel:
    '''
    Checks the health status of the API and DeepSeek token validity.
    
    Returns:
    - ok (bool): True if everything works, False if any error occurs
    - user_id (str | None): user ID from DeepSeek (if token is valid)
    - detail (str | None): error message (if any)
    - service (str): service name ("free-deepseek-api")
    
    Raises:
    - 500: unexpected errors
    '''
    
    health_status = await check_health(ds_session)
    
    return models.HealthModel(
        ok=health_status['ok'], 
        user_id=health_status['user_id'], 
        detail=health_status['detail']
    )