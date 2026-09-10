import os, random
from dotenv import load_dotenv, set_key

load_dotenv()



DEEPSEEK_TOKEN = os.getenv('DEEPSEEK_TOKEN')

DEEPSEEK_SEARCH_ENABLED = False
DEEPSEEK_THINKING_ENABLED = False

BASE_PROMPT_ENABLED = False
BASE_PROMPT = 'Without Markdown: '

SCHEME = 'https://'
AUTHORITY = 'chat.deepseek.com'
API = '/api/v0'
DEEPSEEK_URL = f'{SCHEME}{AUTHORITY}{API}'

HEADERS = {
    'Authorization': f'Bearer {DEEPSEEK_TOKEN}', 
    'Content-Type': 'application/json', 
    'x-client-platform': 'web', 
    'x-client-version': '2.4.0'
}

IMPERSONATE = random.choice(['chrome', 'safari', 'firefox'])



def update_token(new_token: str) -> None:
    global DEEPSEEK_TOKEN, HEADERS
    set_key('.env', 'DEEPSEEK_TOKEN', new_token)
    DEEPSEEK_TOKEN = new_token
    HEADERS = {
        'Authorization': f'Bearer {DEEPSEEK_TOKEN}', 
        'Content-Type': 'application/json', 
        'x-client-platform': 'web', 
        'x-client-version': '2.4.0'
    }