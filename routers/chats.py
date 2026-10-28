from fastapi import APIRouter, status, Depends, Path

from .deps import get_ds_session
from curl_cffi.requests import AsyncSession

from datetime import date, datetime

import models

from src.chats import Chats

chats_router = APIRouter(prefix='/api/chats', tags=['Chats'])



@chats_router.get('')
async def load_chats(start: int | None = None, end: int | None = None, start_date: date | None = None, end_date: date | None = None, ds_session: AsyncSession = Depends(get_ds_session)) -> models.ChatHistoryModel:
    '''
    Gets all chats and returns their parameters.
    
    Query params:
    - start (int | None): the starting index of the chat list (inclusive). Default: 0.
    - end (int | None): the ending index of the chat list (exclusive). Default: None
    - start_date (str | None): filter chats updated on or after this date. Format: YYYY-MM-DD.
    - end_date (str | None): filter chats updated before this date. Format: YYYY-MM-DD.
    
    Behavior:
    - If any date param is provided (start_date or end_date), start and end are ignored:
        - start_date only: returns chats from that date to now.
        - end_date only: returns chats from the beginning up to that date.
        - Both: returns chats within the date range.
    
    - If no date params are provided:
        - start and end: returns range from start to end.
        - start only: returns from start to the last chat.
        - end only: returns from the first chat up to end.
    
    Returns:
    - chats (list[dict]): list of the chats
        - chat_id (str): ID of the chat
        - title (str): title of the chat
        - updated_at (float): timestamp when chat messages were updated
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    - 500: unexpected errors
    - 502: DeepSeek errors (invalid token, wrong message ID or unexpected response format)
    '''
    
    if start_date or end_date:
        if start_date: start_date = datetime.combine(start_date, datetime.min.time()).timestamp()
        if end_date: end_date = datetime.combine(end_date, datetime.min.time()).timestamp()
        chats = await Chats.load_timestamp(ds_session, start_date, end_date)
    else:
        chats = await Chats.load_range(ds_session, start, end)
    
    return models.ChatHistoryModel(
        chats=chats['chats']
    )



@chats_router.delete('', status_code=status.HTTP_204_NO_CONTENT)
async def delete_chats(request: models.DeleteChatsModel, ds_session: AsyncSession = Depends(get_ds_session)) -> None:
    '''
    Deletes multiple chats by their IDs.
    
    Args:
    - chat_ids (list[str]): list of chat IDs to delete
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    - 500: unexpected errors
    - 502: DeepSeek errors (invalid token, wrong message ID or unexpected response format)
    '''
    
    await Chats.delete(ds_session, request.chat_ids)