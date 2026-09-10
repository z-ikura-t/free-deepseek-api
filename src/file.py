import asyncio
from pathlib import Path
from loguru import logger
from mimetypes import guess_type

from curl_cffi import CurlMime
from curl_cffi.requests import AsyncSession

from . import settings
from .utils import extract_from_response
from .pow_challenge import POWChallenge



class Files:
    _max_file_size = 100 * 1024 * 1024
    
    
    @classmethod
    def _failed_file(cls, error_detail: str) -> dict:
        logger.error(f'[Upload Files] Not uploaded | Detail: {error_detail}')
        return {
            'ok': False, 
            'detail': error_detail
        }
    
    
    @classmethod
    async def upload(cls, file_paths: list[str]) -> dict:
        files = []
        async with AsyncSession() as session:
            for file_path in file_paths:
                try:
                    path = Path(file_path)
                    if not path.is_absolute(): files.append(cls._failed_file('File path must be an absolute path')); continue
                    if not path.exists(): files.append(cls._failed_file('File not found')); continue
                    if not path.is_file(): files.append(cls._failed_file('File path must point to a file')); continue
                    if path.stat().st_size > cls._max_file_size: files.append(cls._failed_file('File size exceeds 100 MB limit')); continue
                    content_type, _ = guess_type(str(path))
                    content_type = content_type or 'application/octet-stream'
                    
                    x_ds_pow_response = await POWChallenge.solve(f'{settings.API}/file/upload_file')
                    
                    headers = settings.HEADERS.copy()
                    headers['x-ds-pow-response'] = x_ds_pow_response['result']
                    del headers['Content-Type']
                    
                    multipart = CurlMime()
                    multipart.addpart(
                        name='file', 
                        filename=path.name, 
                        local_path=str(path), 
                        content_type=content_type
                    )
                
                    response = await session.post(
                        f'{settings.DEEPSEEK_URL}/file/upload_file', 
                        headers=headers, 
                        multipart=multipart, 
                        impersonate=settings.IMPERSONATE, 
                        timeout=120
                    )
                    
                    response = extract_from_response('Upload Files', response)
                    
                    file_id = response['data']['biz_data']['id']
                    
                    logger.info(f'[Upload Files] Uploading {path.name}...')
                    
                    attempts = 5
                    error_detail = None
                    for i in range(attempts):
                        response = await session.get(
                            f'{settings.DEEPSEEK_URL}/file/fetch_files', 
                            headers = settings.HEADERS, 
                            params = {'file_ids': file_id}, 
                            impersonate=settings.IMPERSONATE, 
                            timeout=15
                        )
                        
                        response = extract_from_response('Upload Files', response)
                        
                        if not response['data']['biz_data'].get('files'): error_detail = 'File not found in response'; break
                        status = response['data']['biz_data']['files'][0]['status']
                        
                        if status == 'SUCCESS': break
                        elif status == 'CONTENT_EMPTY': error_detail = 'No text could be extracted from the file'; break
                        elif status == 'FAILED': continue
                        
                        await asyncio.sleep(0.5)
                    else: files.append(cls._failed_file('File upload failed')); continue
                    if not error_detail is None: files.append(cls._failed_file(error_detail)); continue
                    
                    files.append({
                        'ok': True, 
                        'file_id': file_id, 
                        'name': path.name, 
                        'size': path.stat().st_size, 
                        'content_type': content_type
                    })
                except Exception as e: files.append(cls._failed_file(f'Error while uploading a file: {str(e)}')); continue
            
            logger.info(f'[Upload Files] Uploaded | Files count: {len(files)}')
            return {
                'files': files
            }