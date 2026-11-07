from typing import Literal, Annotated
from pydantic import BaseModel, Field, ConfigDict, BeforeValidator

import uuid



class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True)



def validate_uuid(value: str) -> str:
    uuid.UUID(str(value))

def validate_chat_id(value: str) -> str:
    try: validate_uuid(value)
    except ValueError: raise ValueError('Invalid chat ID format. Must be a valid UUID.')
    return value

ChatIDType = Annotated[str, BeforeValidator(validate_chat_id)]

class ChatIDMixin(FrozenModel):
    chat_id: ChatIDType



def validate_file_id(value: str) -> str:
    detail = 'Invalid file ID format. Must be a valid UUID with "file-" prefix.'
    
    if not value.startswith('file-'): raise ValueError(detail)
    
    try: validate_uuid(value[5:])
    except ValueError: raise ValueError(detail)
    return value

FileIDType = Annotated[str, BeforeValidator(validate_file_id)]



class HealthModel(FrozenModel):
    ok: bool
    user_id: str | None = Field(min_length=1)
    detail: str | None = Field(min_length=1)
    service: str = Field(min_length=1, default='free-deepseek-api')



class CHChatModel(ChatIDMixin):
    title: str = Field(min_length=1)
    updated_at: float

class ChatHistoryModel(FrozenModel):
    chats: list[CHChatModel]



class DeleteChatsModel(FrozenModel):
    chat_ids: list[ChatIDType] = Field(min_length=1)



class ChatFileModel(FrozenModel):
    file_id: FileIDType
    name: str = Field(min_length=1)
    size: int = Field(ge=1)

class ChatResponseMessageModel(FrozenModel):
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
    current_message_id: int | None = Field(ge=0)
    messages: list[ChatResponseMessageModel]



class RequestNewChatTitleModel(FrozenModel):
    title: str = Field(min_length=1)

class ResponseNewChatTitleModel(ChatIDMixin):
    title: str = Field(min_length=1)



class RequestMessageModel(ChatIDMixin):
    parent_message_id: int | None = Field(ge=2, default=None)
    prompt: str = Field(min_length=1)
    file_ids: list[FileIDType] = Field(default_factory=list)



class RequestRegenerateModel(ChatIDMixin):
    message_id: int = Field(ge=2)



class UserMessageModel(FrozenModel):
    message_id: int = Field(ge=1)
    parent_message_id: int | None = Field(ge=1, default=None)
    role: Literal['USER', 'ASSISTANT']
    content: str = Field(min_length=1)
    files: list[ChatFileModel]

class AssistantMessageModel(FrozenModel):
    message_id: int = Field(ge=1)
    parent_message_id: int | None = Field(ge=1, default=None)
    role: Literal['USER', 'ASSISTANT']
    think: str | None = Field(min_length=1)
    content: str = Field(min_length=1)

class SplitMessageModel(FrozenModel):
    user: UserMessageModel
    assistant: AssistantMessageModel



class FilePathsModel(FrozenModel):
    file_paths: list[str] = Field(min_length=1)

class UploadedFileModel(FrozenModel):
    ok: bool
    file_id: FileIDType | None = None
    name: str | None = Field(min_length=1, default=None)
    size: int | None = Field(ge=1, default=None)
    content_type: str | None = Field(min_length=1, default=None)
    detail: str | None = Field(min_length=1, default=None)

class UploadedFilesModel(FrozenModel):
    files: list[UploadedFileModel]



class ResponseVoiceModel(FrozenModel):
    voice_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    gender: Literal['female', 'male']
    language_count: int = Field(ge=0)

class ResponseVoicesModel(FrozenModel):
    voices: list[ResponseVoiceModel]

class VoiceModel(FrozenModel):
    voice_id: str = Field(min_length=1)



class EnabledModel(FrozenModel):
    enabled: bool

class ValueModel(FrozenModel):
    value: str = Field(min_length=1)