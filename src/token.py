from fastapi import APIRouter, status, Depends

from .deps import get_ds_session
from curl_cffi.requests import AsyncSession

from . import models

from .services import credentials, settings

token_router = APIRouter(prefix='/api/token', tags=['Token'])



@token_router.get('')
async def get_token() -> models.ValueModel:
    '''
    Returns the user's DeepSeek API token.
    
    Returns:
    - value (str): current DeepSeek API token
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    '''
    
    return models.ValueModel(
        value=settings.DEEPSEEK_TOKEN
    )



@token_router.put('')
async def set_token(payload: models.ValueModel, ds_session: AsyncSession = Depends(get_ds_session)) -> models.ValueModel:
    '''
    Sets the user's DeepSeek API token.
    
    Args:
    - value (str): new DeepSeek API token
    
    Returns:
    - value (str): updated DeepSeek API token
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    - 500: unexpected errors
    - 502: DeepSeek errors (invalid token or unexpected response format)
    '''
    
    await credentials.update_token(ds_session, payload.value)
    
    return models.ValueModel(
        value=settings.DEEPSEEK_TOKEN
    )