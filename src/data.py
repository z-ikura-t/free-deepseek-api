import os, random
from loguru import logger
from dotenv import load_dotenv, set_key

from curl_cffi.requests import AsyncSession

from .utils import extract_from_response
from .exceptions import APIError, UnknownError

load_dotenv()



class Config:
    def __init__(self):
        self._token = os.getenv('DEEPSEEK_TOKEN')
        if not self._token: raise ValueError('DEEPSEEK_TOKEN not found in .env file or is empty')
        
        self.search_enabled = False
        self.thinking_enabled = False
        
        self.base_prompt_enabled = False
        self.base_prompt = 'Without Markdown: '
        
        self.model = 'default'
    
    
    @property
    def token(self) -> str:
        return self._token
    
    @token.setter
    def token(self, new_token: str) -> None:
        set_key('.env', 'DEEPSEEK_TOKEN', new_token)
        self._token = new_token
        DATA.set_headers(self._token)



class Data:
    def __init__(self):
        self.scheme = 'https://'
        self.authority = 'chat.deepseek.com'
        
        self.impersonate = random.choice(['chrome', 'safari', 'firefox'])
    
    
    def set_headers(self, token: str) -> None:
        self.headers = {
            'Authorization': f'Bearer {token}', 
            'Content-Type': 'application/json', 
            'x-client-platform': 'web', 
            'x-client-version': '2.4.0'
        }
    
    
    async def check_health(self) -> dict:
        try:
            async with AsyncSession() as session:
                response = await session.get(
                    f'{self.scheme}{self.authority}/api/v0/users/current', 
                    headers=self.headers, 
                    impersonate=self.impersonate, 
                    timeout=10
                )
            
            response = extract_from_response('Health', response)
            
            if not response['data']['biz_data'].get('id') is None:
                user_id = response['data']['biz_data']['id']
                logger.info(f'[Health] OK | User ID: {user_id}')
                return {
                    'ok': True, 
                    'user_id': user_id
                }
            else:
                detail = 'User ID not found'
                logger.error(f'[Health] Response exception | Detail: {detail}')
                return {
                    'ok': False, 
                    'user_id': None
                }
        except APIError: raise
        except Exception as e:
            detail = str(e)
            logger.exception(f'[Health] Unknown exception | Detail: {detail}')
            raise UnknownError(detail) from e



CONFIG = Config()
DATA = Data()
DATA.set_headers(CONFIG.token)