from loguru import logger
from curl_cffi.requests import AsyncSession, Response

from . import settings
from .utils import extract_from_response, handle_exceptions
from .exceptions import ValidationError, DeepSeekResponseError



class Chats:
    @classmethod
    async def _load_chats(cls, ds_session: AsyncSession, updated_at: float | None = None) -> dict:
        response = await ds_session.get(
            f'{settings.DEEPSEEK_URL}/chat_session/fetch_page', 
            headers=settings.HEADERS, 
            params={} if updated_at is None else {'lte_cursor.pinned': False, 'lte_cursor.updated_at': updated_at}, 
            timeout=25
        )
        
        response = extract_from_response('Load Chats', response)
        return response
    
    
    @classmethod
    async def _log_result(cls, chats: int) -> None:
        logger.info(f'[Load Chats] Loaded {len(chats)} chats')
    
    
    @classmethod
    def _has_more_chats(cls, response: Response) -> bool:
        biz_data = response['data'].get('biz_data')
        if biz_data is None: raise DeepSeekResponseError()
        has_more = biz_data.get('has_more')
        if has_more is None: raise DeepSeekResponseError()
        
        if not has_more: return False
        return True
    
    
    @classmethod
    def _add_chats(cls, chat_sessions: list[dict], chats: dict) -> dict:
        for chat_session in chat_sessions:
            chat_id = chat_session.get('id')
            title = chat_session.get('title')
            updated_at = chat_session.get('updated_at')
            if chat_id is None or title is None or updated_at is None: raise DeepSeekResponseError()
            
            chats['chats'].append({
                'chat_id': chat_id, 
                'title': title, 
                'updated_at': updated_at
            })
        return chats
    
    
    @classmethod
    def _get_updated_at(cls, response: Response) -> float | None:
        biz_data = response['data'].get('biz_data')
        if biz_data is None: raise DeepSeekResponseError()
        chat_sessions = biz_data.get('chat_sessions')
        if not chat_sessions: return None
        updated_at = chat_sessions[-1].get('updated_at')
        if updated_at is None: raise DeepSeekResponseError()
        return updated_at
    
    
    @classmethod
    async def _process_response(cls, ds_session: AsyncSession, response: Response) -> dict | None:
        has_more = cls._has_more_chats(response)
        if not has_more: return None
        
        updated_at = cls._get_updated_at(response)
        if updated_at is None: return None
        
        response = await cls._load_chats(ds_session, updated_at)
        return response
    
    
    @classmethod
    def _get_chat_sessions(cls, response: dict) -> list:
        biz_data = response['data'].get('biz_data')
        if biz_data is None: raise DeepSeekResponseError()
        chat_sessions = biz_data.get('chat_sessions')
        if chat_sessions is None: raise DeepSeekResponseError()
        return chat_sessions
    
    
    @classmethod
    @handle_exceptions(log_tag='Load Chats Range')
    async def load_range(cls, ds_session: AsyncSession, start: int | None = None, end: int | None = None) -> dict:
        if start is None: start = 0
        if start < 0: raise ValidationError('Start index must be greater than or equal to 0')
        if not end is None and end < 1: raise ValidationError('End index must be greater than or equal to 1')
        if not end is None and end < start: raise ValidationError('End index must be greater than or equal to start index')
        
        chats = {'chats': []}
        cursor_chats_count = 100
        
        response = await cls._load_chats(ds_session)
        
        updated_at = cls._get_updated_at(response)
        if updated_at is None:
            await cls._log_result(chats['chats'])
            return chats
        
        for _ in range(start // cursor_chats_count):
            response = await cls._process_response(ds_session, response)
            if response is None:
                await cls._log_result(chats['chats'])
                return chats
        
        chat_sessions = cls._get_chat_sessions(response)
        if len(chat_sessions) <= start % cursor_chats_count:
            await cls._log_result(chats['chats'])
            return chats
        
        last_chat = chat_sessions[start % cursor_chats_count]
        if last_chat:
            updated_at = last_chat.get('updated_at')
            if updated_at is None:
                await cls._log_result(chats['chats'])
                return chats
        else:
            await cls._log_result(chats['chats'])
            return chats
        
        response = await cls._load_chats(ds_session, updated_at)
        
        if not end is None:
            chats_count = end - start
            for _ in range(chats_count // cursor_chats_count):
                chat_sessions = cls._get_chat_sessions(response)
                chats = cls._add_chats(chat_sessions, chats)
                response = await cls._process_response(ds_session, response)
                if response is None:
                    await cls._log_result(chats['chats'])
                    return chats
            
            has_more = cls._has_more_chats(response)
            if not has_more: return chats
            
            k = chats_count % 100
            chat_sessions = cls._get_chat_sessions(response)
            chats = cls._add_chats(chat_sessions[:k], chats)
        else:
            while True:
                chat_sessions = cls._get_chat_sessions(response)
                chats = cls._add_chats(chat_sessions, chats)
                response = await cls._process_response(ds_session, response)
                if response is None:
                    await cls._log_result(chats['chats'])
                    return chats
        
        await cls._log_result(chats['chats'])
        return chats
    
    
    @classmethod
    @handle_exceptions(log_tag='Load Chats Timestamp')
    async def load_timestamp(cls, ds_session: AsyncSession, start_timestamp: float | None = None, end_timestamp: float | None = None) -> dict:
        if start_timestamp and end_timestamp and end_timestamp < start_timestamp: raise ValidationError('End timestamp must be greater than or equal to start timestamp')
        start_timestamp, end_timestamp = end_timestamp, start_timestamp
        
        chats = {'chats': []}
        
        response = await cls._load_chats(ds_session, start_timestamp if not start_timestamp is None else None)
        updated_at = cls._get_updated_at(response)
        if updated_at is None:
            await cls._log_result(chats['chats'])
            return chats
        
        while end_timestamp is None or updated_at > end_timestamp:
            chat_sessions = cls._get_chat_sessions(response)
            chats = cls._add_chats(chat_sessions, chats)
            
            has_more = cls._has_more_chats(response)
            if not has_more:
                await cls._log_result(chats['chats'])
                return chats
            
            updated_at = cls._get_updated_at(response)
            if updated_at is None:
                await cls._log_result(chats['chats'])
                return chats
            elif not end_timestamp is None and updated_at <= end_timestamp: break
            
            response = await cls._load_chats(ds_session, updated_at)
        
        if not end_timestamp is None:
            chat_sessions = cls._get_chat_sessions(response)
            for i, chat_session in enumerate(chat_sessions):
                updated_at = chat_session.get('updated_at')
                if updated_at is None:
                    await cls._log_result(chats['chats'])
                    return chats
                if updated_at <= end_timestamp: break
            chat_sessions = cls._get_chat_sessions(response)
            chats = cls._add_chats(chat_session[:i], chats)
        
        await cls._log_result(chats['chats'])
        return chats
    
    
    @classmethod
    @handle_exceptions(log_tag='Delete Chat')
    async def delete(cls, ds_session: AsyncSession, chat_ids: list[str]) -> None:
        response = await ds_session.post(
            f'{settings.DEEPSEEK_URL}/chat_session/delete', 
            headers=settings.HEADERS, 
            json={
                'chat_session_ids': chat_ids
            }
        )
        
        response = extract_from_response('Delete Chats', response)
        
        logger.info(f'[Delete Chats] Deleted {len(chat_ids)} chats')
        return None