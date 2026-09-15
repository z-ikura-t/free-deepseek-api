from loguru import logger
import ssl, websockets, json

from curl_cffi import AsyncSession

from . import ogg
from .. import settings
from ..credentials import get_ticket
from ..utils import extract_from_response
from ..exceptions import APIError, DeepSeekError, DeepSeekResponseError, UnknownError



class TTS:
    @classmethod
    async def get_audio(cls, chat_id: str, message_id: int) -> dict:
        try:
            opus_packets = []
            
            ticket = await get_ticket('tts')
            ticket = ticket['ticket']
            
            tts_url = f'wss://{settings.AUTHORITY}{settings.API}/chat/tts/?chat_session_id={chat_id}&message_id={message_id}&ticket={ticket}&mode=manual&format=opus'
            
            audio_id = None
            async with websockets.connect(tts_url, ssl=ssl.create_default_context()) as ws:
                message = json.loads(await ws.recv())
                if message['event'] != 'ready': raise DeepSeekError(message.get('msg', 'Unknown DeepSeek error'))
                
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
        except APIError: raise
        except Exception as e:
            detail = str(e)
            logger.exception(f'[TTS] Unknown exception | Detail: {detail}')
            raise UnknownError(detail) from e
    
    
    @classmethod
    async def load_voices(cls) -> dict:
        try:
            async with AsyncSession() as session:
                response = await session.get(
                    f'{settings.DEEPSEEK_URL}/chat/tts/voices', 
                    headers=settings.HEADERS, 
                    impersonate=settings.IMPERSONATE
                )
                
                response = extract_from_response('TTS Voices', response)
                
                available_voices = response['data']['biz_data']['voices']
                current_voice_id = response['data']['biz_data']['current_voice_id']
                voices = []
                for available_voice in available_voices:
                    voices.append({
                        'voice_id': available_voice['voice_id'], 
                        'name': available_voice['name_i18n']['en'], 
                        'description': available_voice['description_i18n']['en'], 
                        'gender': available_voice['gender'], 
                        'language_count': len(available_voice['languages'])
                    })
                
                logger.info(f'[TTS Voices] Received | Voice count: {len(voices)}')
                return {
                    'voices': voices, 
                    'current_voice_id': current_voice_id
                }
        except APIError: raise
        except Exception as e:
            detail = str(e)
            logger.exception(f'[TTS Voices] Unknown exception | Detail: {detail}')
            raise UnknownError(detail) from e
    
    
    @classmethod
    async def set_voice(cls, new_voice_id: str) -> dict:
        try:
            async with AsyncSession() as session:
                response = await session.post(
                    f'{settings.DEEPSEEK_URL}/chat/tts/voice', 
                    headers=settings.HEADERS, 
                    impersonate=settings.IMPERSONATE, 
                    json = {
                        'voice_id': new_voice_id
                    }
                )
            
            response = extract_from_response('TTS Voice', response)
            
            logger.info(f'[TTS Voice] Set | New voice ID: {new_voice_id}')
            return {
                'voice_id': new_voice_id
            }
        except APIError: raise
        except Exception as e:
            detail = str(e)
            logger.exception(f'[TTS Voice] Unknown exception | Detail: {detail}')
            raise UnknownError(detail) from e