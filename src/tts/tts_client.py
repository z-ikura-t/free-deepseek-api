from loguru import logger
import ssl, websockets, json

from . import ogg
from .. import settings
from ..credentials import get_ticket
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
            
            if not opus_packets: raise DeepSeekResponseError('No audio packets received')
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