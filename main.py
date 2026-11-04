from fastapi import FastAPI

from curl_cffi.requests import AsyncSession

import sys
from loguru import logger
from contextlib import asynccontextmanager

from src.tts import tts_router
from src.files import files_router
from src.chat import chat_router
from src.chats import chats_router
from src.token import token_router
from src.health import health_router
from src.features import features_router
from src.message import message_router

from src.exceptions import register_exception_handlers

from src.services import settings, credentials

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

app = FastAPI(title='Free DeepSeek API', lifespan=lifespan)

app.include_router(health_router)
app.include_router(chats_router)
app.include_router(chat_router)
app.include_router(message_router)
app.include_router(files_router)
app.include_router(tts_router)
app.include_router(features_router)
app.include_router(token_router)

register_exception_handlers(app)