from fastapi import APIRouter, status, Depends, HTTPException, Path

from .deps import get_ds_session
from curl_cffi.requests import AsyncSession

import uuid
import models

from src.chat import Chat

chat_router = APIRouter(prefix='/api/chat', tags=['Chat'])



@chat_router.post('/create', status_code=status.HTTP_201_CREATED)
async def create_new_chat(ds_session: AsyncSession = Depends(get_ds_session)) -> models.ChatModel:
    '''
    Creates a chat and returns its parameters.
    
    Returns:
    - chat_id (str): ID of the new chat
    - title (str): None for the new chat
    - inserted_at (float): timestamp when chat was created
    - updated_at (float): timestamp when chat was created
    - current_message_id (None): None for the new chat
    - messages (list): empty list for the new chat
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    - 500: unexpected errors
    - 502: DeepSeek errors (invalid token, wrong message ID or unexpected response format)
    '''
    
    new_chat = await Chat.create(ds_session)
    
    return models.ChatModel(
        chat_id=new_chat['chat_id'],
        title=new_chat['title'],
        inserted_at=new_chat['inserted_at'],
        updated_at=new_chat['updated_at'],
        current_message_id=new_chat['current_message_id'],
        messages=new_chat['messages']
    )



@chat_router.get('/{chat_id}')
async def load_chat(chat_id: uuid.UUID = Path(), ds_session: AsyncSession = Depends(get_ds_session)) -> models.ChatModel:
    '''
    Gets chat by ID and returns its parameters.
    
    Args:
    - chat_id (str): ID of the chat
    
    Returns:
    - chat_id (str): ID of the chat
    - title (str): title of the chat
    - inserted_at (float): timestamp when chat was created
    - updated_at (float): timestamp when chat messages were updated
    - current_message_id (int | None): last message id
    - messages (list[dict]): list of chat messages
        - message_id (int): ID of the message
        - parent_message_id (int | None): ID of the parent message
        - role (str): "USER" if author is user, "ASSISTANT" if author is DeepSeek
        - think (str | None): the model's internal reasoning or chain‑of‑thought text
        - content (str): text of the message
        - files (list[dict]): list of files attached to the message
            - file_id (str): ID of the uploaded file
            - name (str): name of the file
            - size (int): size of the file in bytes
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    - 500: unexpected errors
    - 502: DeepSeek errors (invalid token, wrong message ID or unexpected response format)
    '''
    
    chat = await Chat.load(ds_session, str(chat_id))
    
    return models.ChatModel(
        chat_id=chat['chat_id'], 
        title=chat['title'], 
        inserted_at=chat['inserted_at'], 
        updated_at=chat['updated_at'], 
        current_message_id=chat['current_message_id'], 
        messages=chat['messages']
    )



@chat_router.patch('/{chat_id}/title')
async def update_chat_title(request: models.RequestNewChatTitleModel, chat_id: uuid.UUID = Path(), ds_session: AsyncSession = Depends(get_ds_session)) -> models.ResponseNewChatTitleModel:
    '''
    Updates the title of a chat by its ID.
    
    Args:
    - chat_id (str): ID of the chat to update
    - title (str): new title of the chat
    
    Returns:
    - chat_id (str): ID of the updated chat
    - title (str): new title of the chat
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    - 500: unexpected errors
    - 502: DeepSeek errors (invalid token, wrong message ID or unexpected response format)
    '''
    
    chat = await Chat.update_title(ds_session, str(chat_id), request.title)
    
    return models.ResponseNewChatTitleModel(
        chat_id=chat['chat_id'], 
        title=chat['title']
    )