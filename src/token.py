from dotenv import set_key

from . import settings
from .health import check_health
from .exceptions import DeepSeekError



def update_headers() -> None:
    settings.HEADERS = {
        'Authorization': f'Bearer {settings.DEEPSEEK_TOKEN}', 
        'Content-Type': 'application/json', 
        'x-client-platform': 'web', 
        'x-client-version': '2.5.0'
    }

async def update_token(new_token: str) -> None:
    token = settings.DEEPSEEK_TOKEN
    
    settings.DEEPSEEK_TOKEN = new_token
    update_headers()
    health_status = await check_health()
    if not health_status.get('ok'):
        settings.DEEPSEEK_TOKEN = token
        update_headers()
        raise DeepSeekError(health_status.get('detail', 'Unknown DeepSeek error'))
    else:
        set_key('.env', 'DEEPSEEK_TOKEN', new_token)