from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .services.exceptions import (
    APIError, 
    ValidationError, 
    DeepSeekError, 
    DeepSeekResponseError, 
    DeepSeekSSEError, 
    UnknownError
)



def register_exception_handlers(app: FastAPI):
    @app.exception_handler(ValidationError)
    async def _(request: Request, e: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={'detail': str(e)})
    
    @app.exception_handler(DeepSeekError)
    @app.exception_handler(DeepSeekResponseError)
    @app.exception_handler(DeepSeekSSEError)
    async def _(request: Request, e: APIError) -> JSONResponse:
        return JSONResponse(status_code=502, content={'detail': str(e)})
    
    @app.exception_handler(UnknownError)
    @app.exception_handler(Exception)
    async def _(request: Request, e: UnknownError) -> JSONResponse:
        return JSONResponse(status_code=500, content={'detail': str(e)})