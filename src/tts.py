from fastapi import APIRouter, status, Depends, Path, Response

from .deps import get_ds_session
from curl_cffi.requests import AsyncSession

import uuid
from . import models

from .services.tts.tts_client import TTS

tts_router = APIRouter(prefix='/api/tts', tags=['TTS'])



@tts_router.get('/chat/{chat_id}/message/{message_id}')
async def tts(chat_id: uuid.UUID = Path(), message_id: int = Path(ge=1), ds_session: AsyncSession = Depends(get_ds_session)) -> Response:
    '''
    Generates text-to-speech (TTS) audio for the specified message.
    
    Args:
    - chat_id (str): ID of the chat
    - message_id (int): message ID to convert to speech
    
    Returns:
    - Response: Ogg Opus audio (media type: audio/ogg)
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    - 500: unexpected errors
    - 502: DeepSeek errors (invalid token, wrong message ID or unexpected response format)
    '''
    
    audio = await TTS.get_audio(ds_session, str(chat_id), message_id)
    
    return Response(content=audio['audio_bytes'], media_type='audio/ogg')



@tts_router.get('/voices')
async def load_voices(ds_session: AsyncSession = Depends(get_ds_session)) -> models.ResponseVoicesModel:
    '''
    Returns a list of all TTS voices supported by DeepSeek.
    
    Returns:
    - voices (list[dict]): list of available TTS voices
        - voice_id (str): unique voice ID
        - name (str): display name
        - description (str): short description
        - gender (str): "female" or "male"
        - language_count (int): number of supported languages
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    - 500: unexpected errors
    - 502: DeepSeek errors (invalid token, wrong message ID or unexpected response format)
    '''
    
    voices = await TTS.load_voices(ds_session)
    
    return models.ResponseVoicesModel(
        voices=voices['voices']
    )



@tts_router.get('/voice')
async def get_voice(ds_session: AsyncSession = Depends(get_ds_session)) -> models.VoiceModel:
    '''
    Gets the current TTS voice.
    
    Returns:
    - voice_id (str): currently selected voice ID
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    - 500: unexpected errors
    - 502: DeepSeek errors (invalid token, wrong message ID or unexpected response format)
    '''
    
    voices = await TTS.load_voices(ds_session)
    
    return models.VoiceModel(
        voice_id=voices['current_voice_id']
    )



@tts_router.put('/voice')
async def set_voice(payload: models.VoiceModel, ds_session: AsyncSession = Depends(get_ds_session)) -> models.VoiceModel:
    '''
    Sets the current TTS voice.
    
    Args:
    - voice_id (str): voice ID to set
    
    Returns:
    - voice_id (str): currently selected voice ID
    
    Raises:
    - 422: validation errors (invalid input, wrong format)
    - 500: unexpected errors
    - 502: DeepSeek errors (invalid token, wrong message ID or unexpected response format)
    '''
    
    new_voice_id = await TTS.set_voice(ds_session, payload.voice_id)
    
    return models.VoiceModel(
        voice_id=new_voice_id['voice_id']
    )