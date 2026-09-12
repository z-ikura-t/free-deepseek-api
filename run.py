from fastapi.responses import StreamingResponse
from fastapi import FastAPI, HTTPException, status

import sys, json, uuid
from loguru import logger
from datetime import date, datetime

import models

from src.file import Files
from src.chat import Chat
from src.message import Message
from src.health import check_health
from src.chat_history import ChatHistory

from src import settings
from src.exceptions import (
    ValidationError, 
    DeepSeekError, 
    DeepSeekResponseError, 
    DeepSeekSSEError, 
    UnknownError
)



client = FastAPI(title='Free DeepSeek API')

logger.remove()
logger.add(sys.stderr, level='INFO')
logger.add('logs/client.log', rotation='1 MB', level='INFO')



@client.on_event('startup')
async def init() -> None:
    if not settings.DEEPSEEK_TOKEN: raise ValueError('DEEPSEEK_TOKEN not found in .env file or is empty')



@client.get('/api/health', tags=['Health'])
async def health() -> models.HealthModel:
    '''
    Check the health status of the API and DeepSeek token validity.
    
    Returns:
    - ok (bool): True if everything works, False if any error occurs
    - user_id (str | None): user ID from DeepSeek (if token is valid)
    - detail (str | None): error message (if any)
    - service (str): service name ("free-deepseek-api")
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    - 500: unexpected errors
    '''
    
    try:
        health_status = await check_health()
    except (DeepSeekError, DeepSeekResponseError, UnknownError) as e:
        return models.HealthModel(
            ok=False, 
            detail=str(e)
        )
    
    return models.HealthModel(
        ok=health_status['ok'], 
        user_id=health_status['user_id'], 
        detail=health_status['detail']
    )



@client.get('/api/chats', tags=['Chats'])
async def get_chats(start: int | None = None, end: int | None = None, start_date: date | None = None, end_date: date | None = None) -> models.ChatHistoryModel:
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
    
    try:
        if start_date or end_date:
            if start_date: start_date = datetime.combine(start_date, datetime.min.time()).timestamp()
            if end_date: end_date = datetime.combine(end_date, datetime.min.time()).timestamp()
            chat_history = await ChatHistory.load_timestamp(start_date, end_date)
        else:
            chat_history = await ChatHistory.load_range(start, end)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except (DeepSeekError, DeepSeekResponseError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    except UnknownError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return models.ChatHistoryModel(
        chats=chat_history['chats']
    )



@client.delete('/api/chats', tags=['Chats'], status_code=status.HTTP_204_NO_CONTENT)
async def delete_chats(request: models.DeleteChatsModel) -> None:
    '''
    Delete multiple chats by their IDs.
    
    Args:
    - chat_ids (list[str]): list of chat IDs to delete
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    - 500: unexpected errors
    - 502: DeepSeek errors (invalid token, wrong message ID or unexpected response format)
    '''
    
    try:
        await ChatHistory.delete_chats(request.chat_ids)
    except (DeepSeekError, DeepSeekResponseError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    except UnknownError as e:
        raise HTTPException(status_code=500, detail=str(e))



@client.post('/api/chat/create', tags=['Chat'], status_code=status.HTTP_201_CREATED)
async def create_new_chat() -> models.ChatModel:
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
    
    try:
        new_chat = await Chat.create()
    except (DeepSeekError, DeepSeekResponseError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    except UnknownError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return models.ChatModel(
        chat_id=new_chat['chat_id'],
        title=new_chat['title'],
        inserted_at=new_chat['inserted_at'],
        updated_at=new_chat['updated_at'],
        current_message_id=new_chat['current_message_id'],
        messages=new_chat['messages']
    )



@client.get('/api/chat/{chat_id}', tags=['Chat'])
async def get_chat(chat_id: str) -> models.ChatModel:
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
    
    try: uuid.UUID(chat_id)
    except ValueError: raise HTTPException(status_code=422, detail='Invalid chat ID format. Must be a valid UUID.')
    
    try:
        chat = await Chat.load(chat_id)
    except (DeepSeekError, DeepSeekResponseError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    except UnknownError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return models.ChatModel(
        chat_id=chat['chat_id'], 
        title=chat['title'], 
        inserted_at=chat['inserted_at'], 
        updated_at=chat['updated_at'], 
        current_message_id=chat['current_message_id'], 
        messages=chat['messages']
    )



@client.patch('/api/chat/{chat_id}/title', tags=['Chat'])
async def update_chat_title(chat_id: str, request: models.RequestNewChatTitleModel) -> models.ResponseNewChatTitleModel:
    '''
    Update the title of a chat by its ID.
    
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
    
    try: uuid.UUID(chat_id)
    except ValueError: raise HTTPException(status_code=422, detail='Invalid chat ID format. Must be a valid UUID.')
    
    try:
        chat = await Chat.update_title(chat_id, request.title)
    except (DeepSeekError, DeepSeekResponseError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    except UnknownError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return models.ResponseNewChatTitleModel(
        chat_id=chat['chat_id'], 
        title=chat['title']
    )



@client.post('/api/files/upload', tags=['Files'], status_code=status.HTTP_201_CREATED)
async def upload_files(request: models.FilePathsModel) -> models.UploadedFilesModel:
    '''
    Upload one or more files to the DeepSeek server.
    
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
    
    uploaded_files = await Files.upload(request.file_paths)
    
    return models.UploadedFilesModel(
        files=uploaded_files['files']
    )



@client.post('/api/chat/generate', tags=['Messages'], status_code=status.HTTP_201_CREATED, response_model=None)
async def generate(request: models.RequestMessageModel, stream: bool = False) -> models.SplitMessageModel | StreamingResponse:
    '''
    Create a new user message in the chat and generate an assistant response.
    
    Query params:
    - stream (bool): enable Server-Sent Events (SSE) streaming. If True, response is sent as a stream of events. Default is False.
    
    Args:
    - chat_id (str): ID of the chat
    - parent_message_id (int | None): ID of the parent message (None for the first message in a chat)
    - prompt (str): text of the message
    - file_ids (list[str]): list of the uploaded file ids
    
    Returns:
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
        - role (str): "USER" for the user message
        - think (str | None): the model's internal reasoning or chain‑of‑thought text
        - content (str): text of the message
        - files (list[dict]): list of files attached to the message
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    - 500: unexpected errors
    - 502: DeepSeek errors (invalid token, wrong message ID or unexpected response format)
    '''
    
    if not stream:
        try:
            message = await Message.generate_json(request.chat_id, request.parent_message_id, request.prompt, file_ids=request.file_ids)
            
            user = models.UserMessageModel(
                message_id=message['parent_message_id'],
                parent_message_id=request.parent_message_id,
                role='USER',
                content=request.prompt, 
                files=message['files']
            )
            assistant = models.AssistantMessageModel(
                message_id=message['message_id'],
                parent_message_id=message['parent_message_id'],
                role='ASSISTANT',
                think=message['think'],
                content=message['content']
            )
            
            return models.SplitMessageModel(
                user=user, 
                assistant=assistant
            )
        except (DeepSeekError, DeepSeekResponseError, DeepSeekSSEError) as e:
            raise HTTPException(status_code=502, detail=str(e))
        except UnknownError as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        return StreamingResponse(
            Message.generate_stream(request.chat_id, request.parent_message_id, request.prompt, file_ids=request.file_ids), 
            media_type='text/event-stream'
        )



@client.get('/api/feature/search/enabled', tags=['Search'])
async def get_search() -> models.EnabledModel:
    '''
    Returns whether the DeepSeek search feature is enabled.
    
    Search allows DeepSeek to retrieve real-time information from the internet.
    
    Returns:
    - enabled (bool): True if search is enabled, False otherwise
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    '''
    
    return models.EnabledModel(
        enabled=settings.DEEPSEEK_SEARCH_ENABLED
    )



@client.put('/api/feature/search/enabled', tags=['Search'])
async def set_search(request: models.EnabledModel) -> models.EnabledModel:
    '''
    Sets the DeepSeek search feature state.
    
    Search allows DeepSeek to retrieve real-time information from the internet.
    
    Args:
    - enabled (bool): True if search is enabled, False otherwise
    
    Returns:
    - enabled (bool): True if search is enabled, False otherwise
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    '''
    
    settings.DEEPSEEK_SEARCH_ENABLED = request.enabled
    
    return models.EnabledModel(
        enabled=settings.DEEPSEEK_SEARCH_ENABLED
    )



@client.get('/api/feature/thinking/enabled', tags=['Thinking'])
async def get_thinking() -> models.EnabledModel:
    '''
    Returns whether the DeepSeek thinking feature is enabled.
    
    Thinking enables DeepSeek to perform chain-of-thought reasoning before generating a response, improving accuracy on complex tasks.
    
    Returns:
    - enabled (bool): True if thinking is enabled, False otherwise
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    '''
    
    return models.EnabledModel(
        enabled=settings.DEEPSEEK_THINKING_ENABLED
    )



@client.put('/api/feature/thinking/enabled', tags=['Thinking'])
async def set_thinking(request: models.EnabledModel) -> models.EnabledModel:
    '''
    Sets the DeepSeek thinking feature state.
    
    Thinking enables DeepSeek to perform chain-of-thought reasoning before generating a response, improving accuracy on complex tasks.
    
    Args:
    - enabled (bool): True if thinking is enabled, False otherwise
    
    Returns:
    - enabled (bool): True if thinking is enabled, False otherwise
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    '''
    
    settings.DEEPSEEK_THINKING_ENABLED = request.enabled
    
    return models.EnabledModel(
        enabled=settings.DEEPSEEK_THINKING_ENABLED
    )



@client.get('/api/token', tags=['Token'])
async def get_token() -> models.ValueModel:
    '''
    Returns the user's DeepSeek API token.
    
    Returns:
    - value (str): current DeepSeek API token
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    '''
    
    return models.ValueModel(
        value=settings.DEEPSEEK_TOKEN
    )



@client.put('/api/token', tags=['Token'])
async def set_token(request: models.ValueModel) -> models.ValueModel:
    '''
    Sets the user's DeepSeek API token.
    
    Args:
    - value (str): new DeepSeek API token
    
    Returns:
    - value (str): updated DeepSeek API token
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    - 500: unexpected errors
    - 502: DeepSeek errors (invalid token or unexpected response format)
    '''
    
    settings.update_token(request.value)
    
    try:
        health_status = await check_health()
        if not health_status.get('ok'): raise UnknownError(health_status.get('detail', 'Unknown API error'))
    except (DeepSeekError, DeepSeekResponseError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    except UnknownError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return models.ValueModel(
        value=settings.DEEPSEEK_TOKEN
    )