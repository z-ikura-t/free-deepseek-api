import os, random
from dotenv import load_dotenv, set_key

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
    def __init__(self, config: Config):
        self.scheme = 'https://'
        self.authority = 'chat.deepseek.com'
        
        self.headers = {
            'Authorization': f'Bearer {config.token}', 
            'Content-Type': 'application/json', 
            'x-client-platform': 'web', 
            'x-client-version': '2.3.0'
        }
        
        self.impersonate = random.choice(['chrome', 'safari', 'firefox'])
        
        self.debug = False