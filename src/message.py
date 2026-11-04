from fastapi import APIRouter, status, Depends
from fastapi.responses import StreamingResponse

from .deps import get_ds_session
from curl_cffi.requests import AsyncSession

from . import models

from .services.message import Message

message_router = APIRouter(prefix='/api/chat', tags=['Message'])




@message_router.post('/completions', status_code=status.HTTP_201_CREATED)
async def completion(payload: models.RequestMessageModel, ds_session: AsyncSession = Depends(get_ds_session)) -> models.SplitMessageModel:
    '''
    Creates a new user message in the chat and generates an assistant response.
    
    Args:
    - chat_id (str): ID of the chat
    - parent_message_id (int | None): ID of the parent message (None for the first message in a chat)
    - prompt (str): text of the message
    - file_ids (list[str]): list of the uploaded file ids
    
    Returns:
    
    Complete JSON response:
    - user (dict): user message object
        - message_id (int): ID of the message
        - parent_message_id (int | None): ID of the parent message (None for the first message in a chat)
        - role (str): "USER" for the user message
        - content (str): text of the message
        - files (list[dict]): list of files attached to the message
            - file_id (str): ID of the uploaded file
            - name (str): name of the file
            - size (int): size of the file in bytes
        
    - assistant (dict): assistant message object
        - message_id (int): ID of the message
        - parent_message_id (int | None): ID of the parent message (None for the first message in a chat)
        - role (str): "ASSISTANT" for the assistant message
        - think (str | None): the model's internal reasoning or chain‑of‑thought text
        - content (str): text of the message
        - files (list[dict]): list of files attached to the message
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    - 500: unexpected errors
    - 502: DeepSeek errors (invalid token, wrong message ID or unexpected response format)
    '''
    
    message = await Message.completion(ds_session, payload.chat_id, payload.parent_message_id, payload.prompt, file_ids=payload.file_ids)
    
    user = models.UserMessageModel(
        message_id=message['user']['message_id'], 
        parent_message_id=message['user']['parent_message_id'], 
        role=message['user']['role'], 
        content=message['user']['content'], 
        files=message['user']['files']
    )
    assistant = models.AssistantMessageModel(
        message_id=message['assistant']['message_id'], 
        parent_message_id=message['assistant']['parent_message_id'], 
        role=message['assistant']['role'], 
        think=message['assistant']['think'], 
        content=message['assistant']['content']
    )
    
    return models.SplitMessageModel(
        user=user, 
        assistant=assistant
    )



@message_router.post('/completions/stream')
async def completion_stream(payload: models.RequestMessageModel, ds_session: AsyncSession = Depends(get_ds_session)) -> StreamingResponse:
    '''
    Creates a new user message in the chat and generates an assistant response.
    
    Args:
    - chat_id (str): ID of the chat
    - parent_message_id (int | None): ID of the parent message (None for the first message in a chat)
    - prompt (str): text of the message
    - file_ids (list[str]): list of the uploaded file ids
    
    Returns:
    
    Server-Sent Events (text/event-stream). Each event is a "data:" line with a JSON object of type:
    - file: attached file metadata.
        - type (str): "file"
        - file_id (str): ID of the uploaded file
        - name (str): name of the file
        - size (int): size of the file in bytes
    - message_data: final message IDs (user and assistant).
        - type (str): "message_data"
        - message_id (int): ID of the message
        - parent_message_id (int | None): ID of the parent message
        - role (str): "USER" or "ASSISTANT"
    - think: chunk of the model's internal reasoning (chain-of-thought).
        - type (str): "think"
        - content (str): reasoning text chunk
    - response: chunk of the final answer text.
        - type (str): "response"
        - content (str): answer text chunk
    - error: error occurred during streaming.
        - type (str): "error"
        - error (str): error description
    '''
    
    return StreamingResponse(
        Message.completion_stream(ds_session, payload.chat_id, payload.parent_message_id, payload.prompt, file_ids=payload.file_ids), 
        media_type='text/event-stream'
    )



@message_router.post('/regenerate', status_code=status.HTTP_201_CREATED)
async def regenerate(payload: models.RequestRegenerateModel, ds_session: AsyncSession = Depends(get_ds_session)) -> models.AssistantMessageModel:
    '''
    Regenerates the assistant response for the specified message.
    
    A message can be regenerated a limited number of times.
    
    Args:
    - chat_id (str): ID of the chat
    - message_id (int): ID of the assistant message to regenerate (>= 2)
    
    Returns:
    
    Complete JSON response:
    - message_id (int): ID of the new message
    - parent_message_id (int | None): ID of the parent message
    - role (str): "ASSISTANT"
    - think (str | None): the model's internal reasoning (chain-of-thought)
    - content (str): text of the message
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    - 500: unexpected errors
    - 502: DeepSeek errors (invalid token, wrong message ID or unexpected response format)
    '''
    
    message = await Message.regenerate(ds_session, payload.chat_id, payload.message_id)
    
    return models.AssistantMessageModel(
        message_id=message['message_id'], 
        parent_message_id=message['parent_message_id'], 
        role=message['role'], 
        think=message['think'], 
        content=message['content']
    )



@message_router.post('/regenerate/stream')
async def regenerate_stream(payload: models.RequestRegenerateModel, ds_session: AsyncSession = Depends(get_ds_session)) -> StreamingResponse:
    '''
    Regenerates the assistant response for the specified message using streaming.
    
    A message can be regenerated a limited number of times.
    
    Args:
    - chat_id (str): ID of the chat
    - message_id (int): ID of the assistant message to regenerate (>= 2)
    
    Returns:
    
    Server-Sent Events (text/event-stream). Each event is a "data:" line with a JSON object of type:
    - message_data: new message IDs (assistant).
        - type (str): "message_data"
        - message_id (int): ID of the new message
        - parent_message_id (int | None): ID of the parent message
        - role (str): "ASSISTANT"
    - think: chunk of the model's internal reasoning (chain-of-thought).
        - type (str): "think"
        - content (str): reasoning text chunk
    - response: chunk of the final answer text.
        - type (str): "response"
        - content (str): answer text chunk
    - error: error occurred during streaming.
        - type (str): "error"
        - error (str): error description
    '''
    
    return StreamingResponse(
        Message.regenerate_stream(ds_session, payload.chat_id, payload.message_id), 
        media_type='text/event-stream'
    )