import json
from dotenv import set_key
from seleniumbase import SB
from traceback import print_exc

with SB(uc=True, test=False) as sb:
    sb.activate_cdp_mode('https://chat.deepseek.com/sign_in')
    
    input('After authentication, press Enter to continue...')
    
    raw = sb.execute_script('return localStorage.getItem("userToken");')
    
    if raw:
        try:
            data = json.loads(raw)
            token = data.get('value')
            if token:
                set_key('.env', 'DEEPSEEK_TOKEN', token)
                print(f'Token saved to .env')
            else:
                print(f'Token is empty')
        except Exception as e:
            print(f'Unknown exception occurred')
            print_exc()
    else:
        print('Token not found in localStorage')