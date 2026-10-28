from fastapi import APIRouter, status, Depends, HTTPException, Path

from .deps import get_ds_session

import models

from src import settings

feature_router = APIRouter(prefix='/api/feature')



@feature_router.get('/search/enabled', tags=['Search'])
async def get_search() -> models.EnabledModel:
    '''
    Returns whether the DeepSeek search feature is enabled.
    
    Search allows DeepSeek to retrieve real-time information from the internet.
    
    Returns:
    - enabled (bool): True if search is enabled, False otherwise
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    '''
    
    return models.EnabledModel(
        enabled=settings.DEEPSEEK_SEARCH_ENABLED
    )



@feature_router.put('/search/enabled', tags=['Search'])
async def set_search(request: models.EnabledModel) -> models.EnabledModel:
    '''
    Sets the DeepSeek search feature state.
    
    Search allows DeepSeek to retrieve real-time information from the internet.
    
    Args:
    - enabled (bool): True if search is enabled, False otherwise
    
    Returns:
    - enabled (bool): True if search is enabled, False otherwise
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    '''
    
    settings.DEEPSEEK_SEARCH_ENABLED = request.enabled
    
    return models.EnabledModel(
        enabled=settings.DEEPSEEK_SEARCH_ENABLED
    )



@feature_router.get('/thinking/enabled', tags=['Thinking'])
async def get_thinking() -> models.EnabledModel:
    '''
    Returns whether the DeepSeek thinking feature is enabled.
    
    Thinking enables DeepSeek to perform chain-of-thought reasoning before generating a response, improving accuracy on complex tasks.
    
    Returns:
    - enabled (bool): True if thinking is enabled, False otherwise
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    '''
    
    return models.EnabledModel(
        enabled=settings.DEEPSEEK_THINKING_ENABLED
    )



@feature_router.put('/thinking/enabled', tags=['Thinking'])
async def set_thinking(request: models.EnabledModel) -> models.EnabledModel:
    '''
    Sets the DeepSeek thinking feature state.
    
    Thinking enables DeepSeek to perform chain-of-thought reasoning before generating a response, improving accuracy on complex tasks.
    
    Args:
    - enabled (bool): True if thinking is enabled, False otherwise
    
    Returns:
    - enabled (bool): True if thinking is enabled, False otherwise
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    '''
    
    settings.DEEPSEEK_THINKING_ENABLED = request.enabled
    
    return models.EnabledModel(
        enabled=settings.DEEPSEEK_THINKING_ENABLED
    )