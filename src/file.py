import asyncio
from loguru import logger

from curl_cffi import CurlMime
from curl_cffi.requests import AsyncSession

from fastapi import UploadFile

from .data import DATA, CONFIG
from .utils import extract_from_response
from .pow_challenge import POWChallenge
from .exceptions import APIError, DeepSeekResponseError, FileTooLargeError, DeepSeekFileContentEmpty, DeepSeekFileUploadError, UnknownError



class File:
    _max_file_size = 100 * 1024 * 1024
    
    
    @classmethod
    async def upload(cls, file: UploadFile) -> dict:
        try:
            if file.size > cls._max_file_size: raise FileTooLargeError('File size exceeds 100 MB limit')
            
            x_ds_pow_response = await POWChallenge.solve('/api/v0/file/upload_file')
            
            headers = DATA.headers.copy()
            headers['x-ds-pow-response'] = x_ds_pow_response['result']
            del headers['Content-Type']
            if CONFIG.model == 'vision': headers['x-model-type'] = 'vision'
            
            multipart = CurlMime()
            multipart.addpart(
                name='file', 
                content_type=file.content_type, 
                filename=file.filename, 
                data=file.file.read()
            )
            async with AsyncSession() as session:
                response = await session.post(
                    f'{DATA.scheme}{DATA.authority}/api/v0/file/upload_file', 
                    headers=headers, 
                    multipart=multipart, 
                    impersonate=DATA.impersonate, 
                    timeout=120
                )
                
                response = extract_from_response('Upload File', response)
                
                file_id = response['data']['biz_data']['id']
                
                logger.info('[Upload File] Uploading...')
                
                attempts = 5
                for i in range(attempts):
                    response = await session.get(
                        f'{DATA.scheme}{DATA.authority}/api/v0/file/fetch_files', 
                        headers = DATA.headers, 
                        params = {'file_ids': file_id}, 
                        impersonate=DATA.impersonate, 
                        timeout=15
                    )
                    
                    response = extract_from_response('Upload File', response)
                    
                    if not response['data']['biz_data'].get('files'):
                        detail = 'File not found in response'
                        logger.error(f'[Upload File] Not uploaded | Detail: {detail}')
                        raise DeepSeekResponseError(detail)
                    status = response['data']['biz_data']['files'][0]['status']
                    
                    if status == 'SUCCESS': break
                    elif status == 'CONTENT_EMPTY':
                        logger.error('[Upload File] Not uploaded | Status: CONTENT_EMPTY')
                        raise DeepSeekFileContentEmpty('No text could be extracted from the file')
                    elif status == 'FAILED': continue
                    
                    await asyncio.sleep(0.5)
                else:
                    logger.error('[Upload File] Not uploaded | Status: FAILED')
                    raise DeepSeekFileUploadError('File upload failed')
                
                logger.info(f'[Upload File] Uploaded | File name: {file.filename}')
                return {
                    'file_id': file_id
                }
        except APIError: raise
        except Exception as e:
            detail = str(e)
            logger.exception(f'[Upload File] Unknown exception | Detail: {detail}')
            raise UnknownError(detail) from e