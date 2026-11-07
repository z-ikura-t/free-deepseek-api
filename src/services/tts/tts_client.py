from loguru import logger
import ssl, websockets, json

from curl_cffi import AsyncSession

from . import ogg
from .. import settings
from ..credentials import get_ticket
from ..utils import extract_from_response, handle_exceptions
from ..exceptions import DeepSeekError, DeepSeekResponseError



class TTS:
    @classmethod
    @handle_exceptions('TTS')
    async def get_audio(cls, ds_session: AsyncSession, chat_id: str, message_id: int) -> dict:
        opus_packets = []
        
        ticket = await get_ticket(ds_session, 'tts')
        ticket = ticket['ticket']
        
        tts_url = f'wss://{settings.AUTHORITY}{settings.API}/chat/tts/?chat_session_id={chat_id}&message_id={message_id}&ticket={ticket}&mode=manual&format=opus'
        
        audio_id = None
        async with websockets.connect(tts_url, ssl=ssl.create_default_context()) as ws:
            message = json.loads(await ws.recv())
            if message.get('event') != 'ready': raise DeepSeekError(message.get('msg', 'Unknown DeepSeek error'))
            
            audio_id = message.get('audio_id')
            if audio_id is None: raise DeepSeekResponseError('Audio ID is empty')
            logger.info(f'[TTS] Receiving | Audio ID: {audio_id}')
            async for message in ws:
                if isinstance(message, bytes): opus_packets.append(message[4:])
        
        if not opus_packets: raise DeepSeekResponseError(
            'No audio packets received. Only assistant messages can be voiced. '
            'Try changing the voice - the current one may not support this language.'
        )
        ogg_bytes = ogg.build_ogg_opus(opus_packets)
        
        logger.info(f'[TTS] Received | Audio ID: {audio_id}')
        return {
            'audio_id': audio_id, 
            'audio_bytes': ogg_bytes
        }
    
    
    @classmethod
    @handle_exceptions('TTS Voices')
    async def load_voices(cls, ds_session: AsyncSession) -> dict:
        response = await ds_session.get(
            f'{settings.DEEPSEEK_URL}/chat/tts/voices', 
            headers=settings.HEADERS
        )
        
        response = extract_from_response('TTS Voices', response)
        
        biz_data = response['data'].get('biz_data')
        if biz_data is None: raise DeepSeekResponseError()
        
        available_voices = biz_data.get('voices')
        current_voice_id = biz_data.get('current_voice_id')
        if available_voices is None or current_voice_id is None: raise DeepSeekResponseError()
        
        voices = []
        for available_voice in available_voices:
            voice_id = available_voice.get('voice_id')
            voice_name = available_voice.get('name_i18n')
            if voice_name is None: raise DeepSeekResponseError()
            voice_name = voice_name.get('en')
            voice_description = available_voice.get('description_i18n')
            if voice_description is None: raise DeepSeekResponseError()
            voice_description = voice_description.get('en')
            voice_gender = available_voice.get('gender')
            voice_language_count = available_voice.get('languages')
            if voice_id is None or voice_name is None or voice_description is None or voice_gender is None or voice_language_count is None: raise DeepSeekResponseError()
            
            voices.append({
                'voice_id': voice_id, 
                'name': voice_name, 
                'description': voice_description, 
                'gender': voice_gender, 
                'language_count': len(voice_language_count)
            })
        
        logger.info(f'[TTS Voices] Received | Voice count: {len(voices)}')
        return {
            'voices': voices, 
            'current_voice_id': current_voice_id
        }
    
    
    @classmethod
    @handle_exceptions('TTS Voice')
    async def set_voice(cls, ds_session: AsyncSession, new_voice_id: str) -> dict:
        response = await ds_session.post(
            f'{settings.DEEPSEEK_URL}/chat/tts/voice', 
            headers=settings.HEADERS, 
            json = {
                'voice_id': new_voice_id
            }
        )
        
        response = extract_from_response('TTS Voice', response)
        
        logger.info(f'[TTS Voice] Set | New voice ID: {new_voice_id}')
        return {
            'voice_id': new_voice_id
        }