import os, random
from loguru import logger
from traceback import print_exc
from dotenv import load_dotenv, set_key

from curl_cffi.requests import AsyncSession

from .utils import extract_from_response

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



class Data:
    def __init__(self):
        self.scheme = 'https://'
        self.authority = 'chat.deepseek.com'
        
        self.impersonate = random.choice(['chrome', 'safari', 'firefox'])
        
        self.debug = False
        
        self.exception_detail = None
        self.user = {
            'id': None, 
            'token_valid': False
        }
    
    
    def set_headers(self, token: str) -> None:
        self.headers = {
            'Authorization': f'Bearer {token}', 
            'Content-Type': 'application/json', 
            'x-client-platform': 'web', 
            'x-client-version': '2.4.0'
        }
        
        self.exception_detail = None
        self.user = {
            'id': None,
            'token_valid': False
        }
    
    
    async def check_health(self) -> None:
        try:
            async with AsyncSession() as session:
                response = await session.get(
                    f'{self.scheme}{self.authority}/api/v0/users/current', 
                    headers=self.headers, 
                    impersonate=self.impersonate, 
                    timeout=5
                )
            
            response = extract_from_response('Health', response, debug=self.debug)
            if not response[0]:
                self.exception_detail = response[1]
                return None
            else: response = response[1]
            
            if not response['data']['biz_data'].get('id') is None:
                self.user['id'] = response['data']['biz_data']['id']
                self.user['token_valid'] = True
                self.exception_detail = None
                if self.debug: logger.info(f'[Health] OK | User ID: {self.user["id"]}')
            else:
                self.exception_detail = 'user ID not found'
                if self.debug: logger.error(f'[Health] Response exception | Detail: {self.exception_detail}')
        except Exception as e:
            self.exception_detail = str(e)
            if self.debug: logger.error(f'[Health] Unknown exception | Detail: {self.exception_detail}')
            print_exc()