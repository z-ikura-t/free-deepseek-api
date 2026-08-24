from fastapi import FastAPI, HTTPException, File, UploadFile, status

import uuid
from loguru import logger

from src.data import Data
from src.chat import Chat
from src.data import Config
from src.file import File as dsFile
from src.message import Message
from src.chat_history import ChatHistory

import models



client = FastAPI(title='Free DeepSeek API')
config = Config()
data = Data(config)

logger.add('logs/client.log', rotation='1 MB')



@client.get('/api/chats', tags=['Chats'])
async def get_chats(start: int = 0, end: int = 100) -> models.ChatHistoryModel:
    '''
    Gets all chats and returns their parameters.
    
    Query params:
    - start (int): The starting index of the chat list (inclusive).
    - end (int): The ending index of the chat list (exclusive).
    
    Returns:
    - chats (list[dict]): list of the chats
        - chat_id (str): ID of the chat
        - title (str): title of the chat
        - updated_at (float): timestamp when chat messages were updated
        - model_type (str): the DeepSeek model used in the chat
    
    Raises:
    - 422: validation errors
    - 500: unexpected errors
    '''
    
    if start < 0: raise HTTPException(status_code=422, detail='"start" must be greater than or equal to 0')
    elif end < 1: raise HTTPException(status_code=422, detail='"end" must be greater than or equal to 1')
    if end < start: raise HTTPException(status_code=422, detail='"end" must be greater than or equal to "start"')
    
    chat_history = ChatHistory(data)
    await chat_history.fetch(start, end)
    
    if not chat_history.exception_detail is None: raise HTTPException(status_code=500, detail=chat_history.exception_detail)
    
    return models.ChatHistoryModel(
        chats=chat_history.chats
    )



@client.post('/api/chat/create', tags=['Chats'], status_code=status.HTTP_201_CREATED)
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
    - 422: validation errors
    - 500: unexpected errors
    '''
    
    chat = Chat(data)
    await chat.fetch()
    
    if not chat.exception_detail is None: raise HTTPException(status_code=500, detail=chat.exception_detail)
    
    return models.ChatModel(
        chat_id=chat.chat_id,
        title=chat.title,
        inserted_at=chat.inserted_at,
        updated_at=chat.updated_at,
        current_message_id=chat.current_message_id,
        model_type=chat.model_type,
        messages=chat.messages
    )

@client.get('/api/chat/{chat_id}', tags=['Chats'])
async def get_chat(chat_id: str) -> models.ChatModel:
    '''
    Gets chat by id and returns its parameters.
    
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
    - 422: validation errors
    - 500: unexpected errors
    '''
    
    chat = Chat(data)
    await chat.fetch(chat_id)
    
    if not chat.exception_detail is None: raise HTTPException(status_code=500, detail=chat.exception_detail)
    
    return models.ChatModel(
        chat_id=chat.chat_id,
        title=chat.title,
        inserted_at=chat.inserted_at,
        updated_at=chat.updated_at,
        current_message_id=chat.current_message_id,
        model_type=chat.model_type,
        messages=chat.messages
    )



@client.post('/api/chat/generate', tags=['Messages'], status_code=status.HTTP_201_CREATED)
async def generate(request: models.RequestMessageModel) -> models.SplitMessageModel:
    '''
    Create a new user message in the chat and generate an assistant response.
    
    Args:
    - chat_id (str): ID of the chat
    - parent_message_id (int | None): ID of the parent message (None for the first message in a chat)
    - prompt (str): text of the message
    - file_ids (list[str]): list of the uploaded file ids
    
    Returns:
    - user_message (dict): user message object
        - message_id (int): ID of the message
        - parent_message_id (int | None): ID of the parent message (None for the first message in a chat)
        - role (str): "USER" for the user message
        - content (str): text of the message
        - files (list[dict]): list of files attached to the message
            - file_id (str): ID of the uploaded file
            - name (str): name of the file
            - size (int): size of the file in bytes
        
    - assistant_message (dict): assistant message object
        - message_id (int): ID of the message
        - parent_message_id (int | None): ID of the parent message (None for the first message in a chat)
        - role (str): "USER" for the user message
        - think (str | None): the model's internal reasoning or chain‑of‑thought text
        - content (str): text of the message
        - files (list[dict]): list of files attached to the message
    
    Raises:
    - 422: validation errors
    - 500: unexpected errors
    '''
    
    try: uuid.UUID(request.chat_id)
    except ValueError: raise HTTPException(status_code=422, detail='Invalid chat ID format. Must be a valid UUID.')
    
    if config.base_prompt_enabled: request.prompt = f'{config.base_prompt}\n{request.prompt}'
    
    message = Message(data)
    await message.fetch(config, request.chat_id, request.parent_message_id, request.prompt, file_ids=request.file_ids)
    
    if not message.exception_detail is None: raise HTTPException(status_code=500, detail=message.exception_detail)
    
    user_message = models.UserMessageModel(
        message_id=message.parent_message_id,
        parent_message_id=request.parent_message_id,
        role='USER',
        content=request.prompt, 
        files=message.files
    )
    assistant_message = models.AssistantMessageModel(
        message_id=message.message_id,
        parent_message_id=message.parent_message_id,
        role='ASSISTANT',
        think=message.think,
        content=message.reply
    )
    
    return models.SplitMessageModel(
        user_message=user_message, 
        assistant_message=assistant_message
    )



@client.post('/api/file/upload', tags=['File'], status_code=status.HTTP_201_CREATED)
async def upload_file(file: UploadFile = File()) -> models.UploadedFileModel:
    '''
    Upload a file to the DeepSeek server.
    
    Args:
    - file (UploadFile): the uploaded file object
    
    Returns:
    - file_id (str): ID of the uploaded file
    - name (str): name of the file
    - size (int): size of the file in bytes
    - content_type (str): MIME type of the file
    
    Raises:
    - 422: validation errors
    - 500: unexpected errors
    '''
    
    uploaded_file = dsFile(data)
    await uploaded_file.fetch(config, file)
    
    if not uploaded_file.exception_detail is None: raise HTTPException(status_code=500, detail=uploaded_file.exception_detail)
    
    return models.UploadedFileModel(
        file_id=uploaded_file.file_id,
        name=file.filename,
        size=file.size,
        content_type=file.content_type
    )



@client.get('/api/feature/search/enabled', tags=['Search'])
async def get_search() -> models.EnabledModel:
    '''
    Returns whether the DeepSeek search feature is enabled.
    
    Search allows DeepSeek to retrieve real-time information from the internet.
    
    Returns:
    - enabled (bool): True if search is enabled, False otherwise
    
    Raises:
    - 422: validation errors
    '''
    
    return models.EnabledModel(
        enabled=config.search_enabled
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
    - 422: validation errors
    '''
    
    config.search_enabled = request.enabled
    
    return models.EnabledModel(
        enabled=config.search_enabled
    )



@client.get('/api/feature/thinking/enabled', tags=['Thinking'])
async def get_thinking() -> models.EnabledModel:
    '''
    Returns whether the DeepSeek thinking feature is enabled.
    
    Thinking enables DeepSeek to perform chain-of-thought reasoning before generating a response, improving accuracy on complex tasks.
    
    Returns:
    - enabled (bool): True if thinking is enabled, False otherwise
    
    Raises:
    - 422: validation errors
    '''
    
    return models.EnabledModel(
        enabled=config.thinking_enabled
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
    - 422: validation errors
    '''
    
    config.thinking_enabled = request.enabled
    
    return models.EnabledModel(
        enabled=config.thinking_enabled
    )



@client.get('/api/feature/base_prompt/enabled', tags=['Base Prompt'])
async def get_base_prompt_enabled() -> models.EnabledModel:
    '''
    Returns whether the DeepSeek base prompt feature is enabled.
    
    Base prompt is automatically added to the beginning of each user message.
    
    Returns:
    - enabled (bool): True if base prompt is enabled, False otherwise
    
    Raises:
    - 422: validation errors
    '''
    
    return models.EnabledModel(
        enabled=config.base_prompt_enabled
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
    - 422: validation errors
    '''
    
    config.base_prompt_enabled = request.enabled
    
    return models.EnabledModel(
        enabled=config.base_prompt_enabled
    )



@client.get('/api/feature/base_prompt', tags=['Base Prompt'])
async def get_base_prompt() -> models.ValueModel:
    '''
    Returns value of base prompt.
    
    Base prompt is automatically added to the beginning of each user message.
    
    Returns:
    - value (str): current value of the base prompt
    
    Raises:
    - 422: validation errors
    '''
    
    return models.ValueModel(
        value=config.base_prompt
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
    - 422: validation errors
    '''
    
    config.base_prompt = request.value
    
    return models.ValueModel(
        value=config.base_prompt
    )



@client.get('/api/token', tags=['Token'])
async def get_token() -> models.ValueModel:
    '''
    Returns the user's DeepSeek API token.
    
    Returns:
    - value (str): current DeepSeek API token
    
    Raises:
    - 422: validation errors
    '''
    
    return models.ValueModel(
        value=config.token
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
    - 422: validation errors
    '''
    
    config.token = request.value
    
    return models.ValueModel(
        value=config.token
    )



@client.get('/api/model', tags=['Model'])
async def get_model() -> models.DeepSeekModelModel:
    '''
    Returns the DeepSeek model.
    
    Returns:
    - value (str): current DeepSeek model
    
    Raises:
    - 422: validation errors
    '''
    
    return models.DeepSeekModelModel(
        value=config.model
    )

@client.put('/api/model', tags=['Model'])
async def set_model(request: models.DeepSeekModelModel) -> models.DeepSeekModelModel:
    '''
    Sets the DeepSeek model.
    
    Model change applies only to new chats (existing chats keep their original model).
    
    Model variants:
    - "default": instant responses for everyday tasks. Supports internet search, file uploads, and text recognition in images
    - "expert": deep reasoning for complex tasks. Uses a more powerful model with step‑by‑step logic. Does not support file uploads or multimodal features.
    - "vision": image recognition mode. Upload and analyze photos, screenshots, PDFs, and diagrams. Can describe scenes, extract text, and interpret structured data.
    
    Args:
    - value (str): DeepSeek model variant
    
    Returns:
    - value (str): updated DeepSeek model
    
    Raises:
    - 422: validation errors
    '''
    
    config.model = request.value
    
    return models.DeepSeekModelModel(
        value=config.model
    )