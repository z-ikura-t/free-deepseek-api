from loguru import logger
from json import JSONDecodeError

from curl_cffi.requests import Response

from .exceptions import APIError, DeepSeekError, DeepSeekResponseError, UnknownError



def extract_from_response(logs_tag: str, response: Response) -> dict:
    try:
        if response.status_code == 200:
            try: response = response.json()
            except JSONDecodeError:
                detail = f'Invalid JSON response: {response.text[:100]}'
                logger.error(f'[{logs_tag}] Response error | Detail: {detail}')
                raise DeepSeekResponseError(detail)
            
            if response['code'] == 0:
                if response['data']['biz_code'] != 0:
                    detail = response['data']['biz_msg']
                    logger.error(f'[{logs_tag}] DeepSeek error | Detail: {detail}')
                    raise DeepSeekError(detail)
            else:
                detail = response['msg']
                logger.error(f'[{logs_tag}] DeepSeek error | Detail: {detail}')
                raise DeepSeekError(detail)
        else:
            detail = response.text[:100]
            logger.error(f'[{logs_tag}] Response error | Detail: {detail}')
            raise DeepSeekResponseError(detail)
        return response
    except APIError: raise
    except Exception as e:
        detail = str(e)
        logger.exception(f'[{logs_tag}] Unknown error | Detail: {detail}')
        raise UnknownError(detail)