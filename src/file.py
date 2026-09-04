import asyncio
from loguru import logger
from curl_cffi import CurlMime
from traceback import print_exc
from curl_cffi.requests import AsyncSession

from .data import Data, Config
from .utils import extract_from_response
from .pow_challenge import POWChallenge
from fastapi import UploadFile, HTTPException



MAX_FILE_SIZE = 100 * 1024 * 1024



class File:
    def __init__(self, data: Data):
        self._data = data
        
        self.exception_detail = None
        
        self.file_id = None
    
    
    async def fetch(self, config: Config, file: UploadFile) -> None:
        if file.size > MAX_FILE_SIZE: raise HTTPException(status_code=422, detail='File size exceeds 100 MB limit')
        
        try:
            x_ds_pow_response = POWChallenge(self._data)
            await x_ds_pow_response.fetch('/api/v0/file/upload_file')
            if not x_ds_pow_response.exception_detail is None:
                self.exception_detail = x_ds_pow_response.exception_detail
                return None
            
            headers = self._data.headers.copy()
            headers['x-ds-pow-response'] = x_ds_pow_response.result
            del headers['Content-Type']
            if config.model == 'vision': headers['x-model-type'] = 'vision'
            
            multipart = CurlMime()
            multipart.addpart(
                name='file', 
                content_type=file.content_type, 
                filename=file.filename, 
                data=file.file.read()
            )
            async with AsyncSession() as session:
                response = await session.post(
                    f'{self._data.scheme}{self._data.authority}/api/v0/file/upload_file', 
                    headers=headers, 
                    multipart=multipart, 
                    impersonate=self._data.impersonate, 
                    timeout=120
                )
            
            response = extract_from_response('File', response, debug=self._data.debug)
            if not response[0]:
                self.exception_detail = response[1]
                return None
            else: response = response[1]
            
            self.file_id = response['data']['biz_data']['id']
            
            if self._data.debug: logger.info('[File] Uploading...')
            
            attempts = 5
            async with AsyncSession() as session:
                for i in range(attempts):
                    response = await session.get(
                        f'{self._data.scheme}{self._data.authority}/api/v0/file/fetch_files', 
                        headers = self._data.headers, 
                        params = {'file_ids': self.file_id}, 
                        impersonate=self._data.impersonate, 
                        timeout=15
                    )
                    
                    response = extract_from_response('File', response, debug=self._data.debug)
                    if not response[0]:
                        self.exception_detail = response[1]
                        return None
                    else: response = response[1]
                    
                    if response['data']['biz_data'].get('files') is None:
                        self.exception_detail = 'File not found in response'
                        return None
                    status = response['data']['biz_data']['files'][0]['status']
                    
                    if status == 'SUCCESS': break
                    elif status == 'CONTENT_EMPTY':
                        if self._data.debug: logger.error('[File] Not uploaded | Status: CONTENT_EMPTY')
                        self.exception_detail = 'No text could be extracted from the file'
                        return None
                    elif status == 'FAILED': continue
                    
                    await asyncio.sleep(1)
                else:
                    if self._data.debug: logger.error('[File] Not uploaded | Status: FAILED')
                    self.exception_detail = 'File upload failed'
                
                if self._data.debug: logger.info(f'[File] Uploaded | File name: {file.filename}')
        except Exception as e:
            self.exception_detail = str(e)
            if self._data.debug: logger.error(f'[File] Unknown exception | Detail: {self.exception_detail}')
            print_exc()