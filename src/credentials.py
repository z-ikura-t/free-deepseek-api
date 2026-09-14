import asyncio
from loguru import logger
from dotenv import set_key

from curl_cffi import AsyncSession

from . import settings
from .health import check_health
from .utils import extract_from_response
from .exceptions import APIError, DeepSeekError, UnknownError



def update_headers() -> None:
    settings.HEADERS = {
        'Authorization': f'Bearer {settings.DEEPSEEK_TOKEN}', 
        'Content-Type': 'application/json', 
        'x-client-platform': 'web', 
        'x-client-version': '2.5.0'
    }



_token_lock = asyncio.Lock()
async def update_token(new_token: str) -> None:
    async with _token_lock:
        token = settings.DEEPSEEK_TOKEN
        
        health_status = await check_health({
            'Authorization': f'Bearer {new_token}', 
            'Content-Type': 'application/json', 
            'x-client-platform': 'web', 
            'x-client-version': '2.5.0'
        })
        if not health_status.get('ok'): raise DeepSeekError(health_status.get('detail', 'Unknown DeepSeek error'))
        settings.DEEPSEEK_TOKEN = new_token
        update_headers()
        set_key('.env', 'DEEPSEEK_TOKEN', new_token)



async def get_ticket(scope: str) -> dict:
    try:
        async with AsyncSession() as session:
            response = await session.post(
                f'{settings.DEEPSEEK_URL}/auth/ticket', 
                headers=settings.HEADERS, 
                impersonate=settings.IMPERSONATE, 
                json = {
                    'scope': scope
                }
            )
        
        response = extract_from_response('Ticket', response)
        
        ticket = response['data']['biz_data']['ticket']
        expires_in = response['data']['biz_data']['expires_in_secs']
        
        logger.info(f'[Ticket] Received | Expires in: {expires_in}')
        return {
            'ticket': ticket
        }
    except APIError: raise
    except Exception as e:
        detail = str(e)
        logger.exception(f'[Ticket] Unknown exception | Detail: {detail}')
        raise UnknownError(detail) from e