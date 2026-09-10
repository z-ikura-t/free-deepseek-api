from loguru import logger

from curl_cffi.requests import AsyncSession

from . import settings
from .utils import extract_from_response
from .exceptions import APIError, UnknownError



async def check_health() -> dict:
    try:
        if not settings.DEEPSEEK_TOKEN: raise ValueError('DEEPSEEK_TOKEN not found in .env file or is empty')
        
        async with AsyncSession() as session:
            response = await session.get(
                f'{settings.DEEPSEEK_URL}/users/current', 
                headers=settings.HEADERS, 
                impersonate=settings.IMPERSONATE, 
                timeout=10
            )
            
            response = extract_from_response('Health', response)
            
            if not response['data']['biz_data'].get('id') is None:
                user_id = response['data']['biz_data']['id']
                logger.info(f'[Health] OK | User ID: {user_id}')
                return {
                    'ok': True, 
                    'user_id': user_id, 
                    'detail': None
                }
            else:
                detail = 'User ID not found'
                logger.error(f'[Health] Response exception | Detail: {detail}')
                return {
                    'ok': False, 
                    'user_id': None, 
                    'detail': detail
                }
    except (APIError, ValueError): raise
    except Exception as e:
        detail = str(e)
        logger.exception(f'[Health] Unknown exception | Detail: {detail}')
        raise UnknownError(detail) from e