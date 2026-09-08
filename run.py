from fastapi.responses import StreamingResponse
from fastapi import FastAPI, HTTPException, File, UploadFile, status

import sys, json, uuid
from loguru import logger
from datetime import date, datetime

from src.chat import Chat
from src.file import File as dsFile
from src.message import Message
from src.data import DATA, CONFIG
from src.chat_history import ChatHistory
from src.exceptions import DeepSeekError, DeepSeekResponseError, DeepSeekSSEError, UnknownError, FileTooLargeError, DeepSeekFileContentEmpty, DeepSeekFileUploadError

import models



client = FastAPI(title='Free DeepSeek API')

logger.remove()
logger.add(sys.stderr, level='INFO')
logger.add('logs/client.log', rotation='1 MB', level='INFO')



@client.get('/api/health', tags=['Health'])
async def check_health() -> models.HealthModel:
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
        health = await DATA.check_health()
    except (DeepSeekError, DeepSeekResponseError, UnknownError) as e:
        return models.HealthModel(
            ok=False, 
            detail=str(e)
        )
    
    return models.HealthModel(
        ok=True, 
        user_id=health['user_id']
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
        - model_type (str): the DeepSeek model used in the chat
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    - 500: unexpected errors
    - 502: DeepSeek errors (invalid token, wrong message ID or unexpected response format)
    '''
    
    try:
        if start_date or end_date:
            if start_date: start = datetime.combine(start_date, datetime.min.time()).timestamp()
            else: start = None
            if end_date: end = datetime.combine(end_date, datetime.min.time()).timestamp()
            else: end = None
            if start_date and end_date:
                if end < start: raise HTTPException(status_code=422, detail='"end_date" must be greater than or equal to "start_date"')
            
            chat_history = await ChatHistory.load_timestamp(start, end)
        else:
            if not start is None and not end is None:
                if end < start: raise HTTPException(status_code=422, detail='"end" must be greater than or equal to "start"')
            if not start is None:
                if start < 0: raise HTTPException(status_code=422, detail='"start" must be greater than or equal to 0')
            else: start = 0
            if not end is None:
                if end < 1: raise HTTPException(status_code=422, detail='"end" must be greater than or equal to 1')
            else: end = None
            
            chat_history = await ChatHistory.load_range(start, end)
    except HTTPException: raise
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
        chat_history = await ChatHistory.delete_chats(request.chat_ids)
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
    - model_type (str): "default" for the new chat
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
        model_type=new_chat['model_type'],
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
    - model_type (str): the DeepSeek model used in the chat
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
        model_type=chat['model_type'],
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



@client.post('/api/file/upload', tags=['File'], status_code=status.HTTP_201_CREATED)
async def upload_file(file: UploadFile = File()) -> models.UploadedFileModel:
    '''
    Upload a file to the DeepSeek server.
    
    Maximum file size: 100 MB.
    
    Args:
    - file (UploadFile): the uploaded file object
    
    Returns:
    - file_id (str): ID of the uploaded file
    - name (str): name of the file
    - size (int): size of the file in bytes
    - content_type (str): MIME type of the file
    
    Raises:
    - 413: File too large (exceeds 100 MB limit)
    - 422: validation errors (invalid input, wrong format)
    - 500: unexpected errors
    - 502: DeepSeek errors (invalid token, wrong message ID or unexpected response format)
    '''
    
    try:
        uploaded_file = await dsFile.upload(file)
    except (DeepSeekError, DeepSeekResponseError, DeepSeekFileUploadError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    except FileTooLargeError as e:
        raise HTTPException(status_code=413, detail=str(e))
    except DeepSeekFileContentEmpty as e:
        raise HTTPException(status_code=422, detail=str(e))
    except UnknownError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return models.UploadedFileModel(
        file_id=uploaded_file['file_id'],
        name=file.filename,
        size=file.size,
        content_type=file.content_type
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
        except (DeepSeekError, DeepSeekResponseError) as e:
            raise HTTPException(status_code=502, detail=str(e))
        except UnknownError as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        return StreamingResponse(
            Message.generate_stream(request.chat_id, request.parent_message_id, request.prompt, file_ids=request.file_ids), 
            media_type='text/event-stream'
        )



@client.get('/api/model', tags=['Model'])
async def get_model() -> models.DeepSeekModelModel:
    '''
    Returns the DeepSeek model.
    
    Returns:
    - value (str): current DeepSeek model
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    '''
    
    return models.DeepSeekModelModel(
        value=CONFIG.model
    )



@client.put('/api/model', tags=['Model'])
async def set_model(request: models.DeepSeekModelModel) -> models.DeepSeekModelModel:
    '''
    Sets the DeepSeek model.
    
    Model change applies only to new chats (existing chats keep their original model).
    
    Model variants:
    - DeepSeek-V4-Flash, 284B / 13B ("default"): instant responses for everyday tasks. Supports internet search, file uploads, and text recognition in images
    - DeepSeek-V4-Pro, 1.6T / 49B ("expert"): deep reasoning for complex tasks. Uses a more powerful model with step‑by‑step logic. Does not support file uploads or multimodal features.
    - DeepSeek-V4-Flash-Vision-Exp, 284B / 13B ("vision"): image recognition mode. Upload and analyze photos, screenshots, PDFs, and diagrams. Can describe scenes, extract text, and interpret structured data.
    
    Args:
    - value (str): DeepSeek model variant
    
    Returns:
    - value (str): updated DeepSeek model
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    '''
    
    CONFIG.model = request.value
    
    return models.DeepSeekModelModel(
        value=CONFIG.model
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
        enabled=CONFIG.search_enabled
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
    
    CONFIG.search_enabled = request.enabled
    
    return models.EnabledModel(
        enabled=CONFIG.search_enabled
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
        enabled=CONFIG.thinking_enabled
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
    
    CONFIG.thinking_enabled = request.enabled
    
    return models.EnabledModel(
        enabled=CONFIG.thinking_enabled
    )



@client.get('/api/feature/base_prompt/enabled', tags=['Base Prompt'])
async def get_base_prompt_enabled() -> models.EnabledModel:
    '''
    Returns whether the DeepSeek base prompt feature is enabled.
    
    Base prompt is automatically added to the beginning of each user message.
    
    Returns:
    - enabled (bool): True if base prompt is enabled, False otherwise
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    '''
    
    return models.EnabledModel(
        enabled=CONFIG.base_prompt_enabled
    )



@client.put('/api/feature/base_prompt/enabled', tags=['Base Prompt'])
async def set_base_prompt_enabled(request: models.EnabledModel) -> models.EnabledModel:
    '''
    Sets the DeepSeek base prompt feature state.
    
    Base prompt is automatically added to the beginning of each user message.
    
    Args:
    - enabled (bool): True if base prompt is enabled, False otherwise
    
    Returns:
    - enabled (bool): True if base prompt is enabled, False otherwise
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    '''
    
    CONFIG.base_prompt_enabled = request.enabled
    
    return models.EnabledModel(
        enabled=CONFIG.base_prompt_enabled
    )



@client.get('/api/feature/base_prompt', tags=['Base Prompt'])
async def get_base_prompt() -> models.ValueModel:
    '''
    Returns value of base prompt.
    
    Base prompt is automatically added to the beginning of each user message.
    
    Returns:
    - value (str): current value of the base prompt
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    '''
    
    return models.ValueModel(
        value=CONFIG.base_prompt
    )



@client.put('/api/feature/base_prompt', tags=['Base Prompt'])
async def set_base_prompt(request: models.ValueModel) -> models.ValueModel:
    '''
    Sets the base prompt value.
    
    Base prompt is automatically added to the beginning of each user message.
    
    Args:
    - value (str): new value of the base prompt
    
    Returns:
    - value (str): updated value of the base prompt
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    '''
    
    CONFIG.base_prompt = request.value
    
    return models.ValueModel(
        value=CONFIG.base_prompt
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
        value=CONFIG.token
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
    
    CONFIG.token = request.value
    
    try:
        health = await DATA.check_health()
    except (DeepSeekError, DeepSeekResponseError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    except UnknownError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return models.ValueModel(
        value=CONFIG.token
    )