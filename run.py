from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from curl_cffi.requests import AsyncSession

import sys
from loguru import logger
from contextlib import asynccontextmanager

from routers.tts import tts_router
from routers.files import files_router
from routers.chat import chat_router
from routers.chats import chats_router
from routers.token import token_router
from routers.health import health_router
from routers.feature import feature_router
from routers.message import message_router

from src import settings, credentials
from src.exceptions import (
    APIError, 
    ValidationError, 
    DeepSeekError, 
    DeepSeekResponseError, 
    DeepSeekSSEError, 
    UnknownError
)

logger.remove()
logger.add(sys.stderr, level='INFO')
logger.add('logs/client.log', rotation='1 MB', level='INFO')



@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.DEEPSEEK_TOKEN: raise ValueError('DEEPSEEK_TOKEN not found in .env file or is empty')
    
    credentials.update_headers()
    
    app.state.ds_session = AsyncSession(
        impersonate=settings.IMPERSONATE, 
        timeout=30
    )
    try: yield
    finally: await app.state.ds_session.close()

client = FastAPI(title='Free DeepSeek API', lifespan=lifespan)

client.include_router(health_router)
client.include_router(chats_router)
client.include_router(chat_router)
client.include_router(message_router)
client.include_router(files_router)
client.include_router(tts_router)
client.include_router(feature_router)
client.include_router(token_router)



@client.exception_handler(ValidationError)
async def _(request: Request, e: ValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={'detail': str(e)})

@client.exception_handler(DeepSeekError)
@client.exception_handler(DeepSeekResponseError)
@client.exception_handler(DeepSeekSSEError)
async def _(request: Request, e: APIError) -> JSONResponse:
    return JSONResponse(status_code=502, content={'detail': str(e)})

@client.exception_handler(UnknownError)
@client.exception_handler(Exception)
async def _(request: Request, e: UnknownError) -> JSONResponse:
    return JSONResponse(status_code=500, content={'detail': str(e)})