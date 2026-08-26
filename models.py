from pydantic import BaseModel, Field, validator
from typing import Literal

import uuid



class ChatIDMixin(BaseModel):
    chat_id: str = Field(min_length=36, max_length=36)
    
    @validator('chat_id')
    def validate_chat_id(cls, value: str) -> str:
        try: uuid.UUID(value)
        except ValueError: raise ValueError('Invalid chat ID format. Must be a valid UUID.')
        return value



class CHChatModel(ChatIDMixin):
    title: str = Field(min_length=1)
    updated_at: float
    model_type: Literal['default', 'expert', 'vision']

class ChatHistoryModel(BaseModel):
    chats: list[CHChatModel]



class DeleteChatsModel(BaseModel):
    chat_ids: list[str] = Field(min_length=36, max_length=36)
    
    @validator('chat_ids', each_item=True)
    def validate_chat_id(cls, value: str) -> str:
        try: uuid.UUID(value)
        except ValueError: raise ValueError('Invalid chat ID format. Must be a valid UUID.')
        return value



class ChatFileModel(BaseModel):
    file_id: str = Field(min_length=41, max_length=41)
    name: str = Field(min_length=1)
    size: int = Field(ge=1)

class ChatResponseMessageModel(BaseModel):
    message_id: int = Field(ge=1)
    parent_message_id: int | None = Field(ge=1, default=None)
    role: Literal['USER', 'ASSISTANT']
    think: str | None = Field(min_length=1)
    content: str = Field(min_length=0)
    files: list[ChatFileModel]

class ChatModel(ChatIDMixin):
    title: str | None = Field(min_length=1)
    inserted_at: float
    updated_at: float
    model_type: Literal['default', 'expert', 'vision']
    current_message_id: int | None = Field(ge=0)
    messages: list[ChatResponseMessageModel]



class RequestNewChatTitleModel(BaseModel):
    title: str = Field(min_length=1)

class ResponseNewChatTitleModel(ChatIDMixin):
    title: str = Field(min_length=1)


class RequestMessageModel(ChatIDMixin):
    parent_message_id: int | None = Field(ge=1, default=None)
    prompt: str = Field(min_length=1)
    file_ids: list[str] = Field(min_length=41, max_length=41)



class UserMessageModel(BaseModel):
    message_id: int = Field(ge=1)
    parent_message_id: int | None = Field(ge=1, default=None)
    role: Literal['USER', 'ASSISTANT']
    content: str = Field(min_length=1)
    files: list[ChatFileModel]

class AssistantMessageModel(BaseModel):
    message_id: int = Field(ge=1)
    parent_message_id: int | None = Field(ge=1, default=None)
    role: Literal['USER', 'ASSISTANT']
    think: str | None = Field(min_length=1)
    content: str = Field(min_length=1)

class SplitMessageModel(BaseModel):
    user_message: UserMessageModel
    assistant_message: AssistantMessageModel



class UploadedFileModel(BaseModel):
    file_id: str = Field(min_length=41, max_length=41)
    name: str = Field(min_length=1)
    size: int = Field(ge=1)
    content_type: str = Field(min_length=1)



class EnabledModel(BaseModel):
    enabled: bool

class ValueModel(BaseModel):
    value: str = Field(min_length=1)



class DeepSeekModelModel(BaseModel):
    value: Literal['default', 'expert', 'vision']