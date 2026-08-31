from loguru import logger
from traceback import print_exc
from json import JSONDecodeError

from curl_cffi.requests import Response



def extract_from_response(tag: str, response: Response, debug: bool = False) -> tuple[bool, dict | str]:
    try:
        if response.status_code == 200:
            try:
                response = response.json()
            except JSONDecodeError:
                exception_detail = f'Invalid JSON response: {response.text[:100]}'
                if debug: logger.error(f'[{tag}] Response exception | Detail: {exception_detail}')
                return (False, exception_detail)
            
            if response['code'] == 0:
                if response['data']['biz_code'] != 0:
                    exception_detail = response['data']['biz_msg']
                    if debug: logger.error(f'[{tag}] DeepSeek exception | Detail: {exception_detail}')
                    return (False, exception_detail)
            else:
                exception_detail = response['msg']
                if debug: logger.error(f'[{tag}] DeepSeek exception | Detail: {exception_detail}')
                return (False, exception_detail)
        else:
            exception_detail = response.text
            if debug: logger.error(f'[{tag}] Response exception | Detail: {exception_detail}')
            return (False, exception_detail)
        return (True, response)
    except Exception as e:
        exception_detail = str(e)
        if debug: logger.error(f'[{tag}] Unknown exception | Detail: {exception_detail}')
        print_exc()
        return (False, exception_detail)