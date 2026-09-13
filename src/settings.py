import os, random
from dotenv import load_dotenv

load_dotenv()



DEEPSEEK_TOKEN = os.getenv('DEEPSEEK_TOKEN')

DEEPSEEK_SEARCH_ENABLED = False
DEEPSEEK_THINKING_ENABLED = False

SCHEME = 'https://'
AUTHORITY = 'chat.deepseek.com'
API = '/api/v0'
DEEPSEEK_URL = f'{SCHEME}{AUTHORITY}{API}'

HEADERS = {
    'Authorization': f'Bearer {DEEPSEEK_TOKEN}', 
    'Content-Type': 'application/json', 
    'x-client-platform': 'web', 
    'x-client-version': '2.5.0'
}

IMPERSONATE = random.choice(['chrome', 'safari', 'firefox'])