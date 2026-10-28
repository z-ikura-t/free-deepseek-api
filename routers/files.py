from fastapi import APIRouter, status, Depends

from .deps import get_ds_session
from curl_cffi.requests import AsyncSession

import models

from src.files import Files

files_router = APIRouter(prefix='/api/files', tags=['Files'])



@files_router.post('/upload', status_code=status.HTTP_201_CREATED)
async def upload_files(request: models.FilePathsModel, ds_session: AsyncSession = Depends(get_ds_session)) -> models.UploadedFilesModel:
    '''
    Uploads one or more files to the DeepSeek server.
    
    Maximum file size: 100 MB per file.
    
    Args:
    - file_paths (list[str]): list of absolute paths to files
    
    Returns:
    - files (list[dict]): list of uploaded files
        - ok (bool): True if uploaded successfully, False otherwise
        - file_id (str | None): ID of the uploaded file
        - name (str | None): name of the file
        - size (int | None): size of the file in bytes
        - content_type (str | None): MIME type of the file
        - detail (str | None): error message (if any)
    
    Raises:
    - 500: unexpected errors
    '''
    
    uploaded_files = await Files.upload(ds_session, request.file_paths)
    
    return models.UploadedFilesModel(
        files=uploaded_files['files']
    )