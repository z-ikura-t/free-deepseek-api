from fastapi import Request

from curl_cffi.requests import AsyncSession



def get_ds_session(request: Request) -> AsyncSession:
    return request.app.state.ds_session