import asyncio
from loguru import logger
from dotenv import set_key

from curl_cffi import AsyncSession

from . import settings
from .health import check_health
from .utils import extract_from_response, handle_exceptions
from .exceptions import DeepSeekError, DeepSeekResponseError



def _get_headers(token: str | None = settings.DEEPSEEK_TOKEN) -> None:
    return {
        'Authorization': f'Bearer {token}', 
        'Content-Type': 'application/json', 
        'x-client-platform': 'web', 
        'x-client-version': settings.DEEPSEEK_CLIENT_VERSION
    }



def update_headers() -> None:
    settings.HEADERS = _get_headers()



_token_lock = asyncio.Lock()
async def update_token(ds_session: AsyncSession, new_token: str) -> None:
    async with _token_lock:
        token = settings.DEEPSEEK_TOKEN
        
        health_status = await check_health(ds_session, _get_headers(new_token))
        if not health_status.get('ok'): raise DeepSeekError(health_status.get('detail', 'Unknown DeepSeek error'))
        
        settings.DEEPSEEK_TOKEN = new_token
        update_headers()
        set_key('.env', 'DEEPSEEK_TOKEN', new_token)



@handle_exceptions(log_tag='Ticket')
async def get_ticket(ds_session: AsyncSession, scope: str) -> dict:
    response = await ds_session.post(
        f'{settings.DEEPSEEK_URL}/auth/ticket', 
        headers=settings.HEADERS, 
        json = {
            'scope': scope
        }
    )
    
    response = extract_from_response('Ticket', response)
    
    biz_data = response['data'].get('biz_data')
    if biz_data is None: raise DeepSeekResponseError()
    ticket = biz_data.get('ticket')
    if ticket is None: raise DeepSeekResponseError()
    expires_in = biz_data.get('expires_in_secs')
    if expires_in is None: raise DeepSeekResponseError()
    
    logger.info(f'[Ticket] Received | Expires in (seconds): {expires_in}')
    return {
        'ticket': ticket, 
        'expires_in_seconds': expires_in
    }