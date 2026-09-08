from loguru import logger
from curl_cffi.requests import AsyncSession, Response

from .data import DATA
from .utils import extract_from_response
from .exceptions import APIError, UnknownError



class ChatHistory:
    _logs_tag = 'Chat History'
    
    
    @classmethod
    async def _get_chats(cls, updated_at: float | None = None) -> dict:
        async with AsyncSession() as session:
            response = await session.get(
                f'{DATA.scheme}{DATA.authority}/api/v0/chat_session/fetch_page', 
                headers=DATA.headers, 
                params={} if updated_at is None else {'lte_cursor.pinned': False, 'lte_cursor.updated_at': updated_at}, 
                impersonate=DATA.impersonate, 
                timeout=10
            )
        
        response = extract_from_response(cls._logs_tag, response)
        return response
    
    
    @classmethod
    async def _log_result(cls, chat_count: int) -> None:
        logger.info(f'[{cls._logs_tag}] Retrieved {chat_count} chats')
    
    
    @classmethod
    def _has_more_chats(cls, response: Response) -> bool:
        has_more = response['data']['biz_data']['has_more']
        if not has_more: return False
        return True
    
    
    @classmethod
    def _add_chats(cls, chat_sessions: list[dict], chats: dict) -> dict:
        for chat_session in chat_sessions:
            chats['chats'].append({
                'chat_id': chat_session['id'], 
                'title': chat_session['title'], 
                'model_type': chat_session['model_type'], 
                'updated_at': chat_session['updated_at']
        })
        return chats
    
    
    @classmethod
    def _get_updated_at(cls, response: Response) -> float | None:
        if not response['data']['biz_data']['chat_sessions']: return None
        updated_at = response['data']['biz_data']['chat_sessions'][-1]['updated_at']
        return updated_at
    
    
    @classmethod
    async def _process_response(cls, response: Response) -> dict | None:
        has_more = cls._has_more_chats(response)
        if not has_more: return None
        
        updated_at = cls._get_updated_at(response)
        if updated_at is None: return None
        
        response = await cls._get_chats(updated_at)
        return response
    
    
    @classmethod
    async def load_range(cls, start: int = 0, end: int | None = None) -> dict:
        try:
            chats = {'chats': []}
            cursor_chats_count = 100
            
            response = await cls._get_chats()
            
            updated_at = cls._get_updated_at(response)
            if updated_at is None:
                await cls._log_result(len(chats['chats']))
                return chats
            
            for _ in range(start // cursor_chats_count):
                response = await cls._process_response(response)
                if response is None:
                    await cls._log_result(len(chats['chats']))
                    return chats
            
            if len(response['data']['biz_data']['chat_sessions']) <= start % cursor_chats_count:
                await cls._log_result(len(chats['chats']))
                return chats
            
            last_chat = response['data']['biz_data']['chat_sessions'][start % cursor_chats_count]
            if last_chat: updated_at = last_chat['updated_at']
            else:
                await cls._log_result(len(chats['chats']))
                return chats
            
            response = await cls._get_chats(updated_at)
            
            if not end is None:
                chats_count = end - start
                for _ in range(chats_count // cursor_chats_count):
                    chats = cls._add_chats(response['data']['biz_data']['chat_sessions'], chats)
                    response = await cls._process_response(response)
                    if response is None:
                        await cls._log_result(len(chats['chats']))
                        return chats
                
                has_more = cls._has_more_chats(response)
                if not has_more: return chats
                
                k = chats_count % 100
                chats = cls._add_chats(response['data']['biz_data']['chat_sessions'][:k], chats)
            else:
                while True:
                    chats = cls._add_chats(response['data']['biz_data']['chat_sessions'], chats)
                    response = await cls._process_response(response)
                    if response is None:
                        await cls._log_result(len(chats['chats']))
                        return chats
            
            await cls._log_result(len(chats['chats']))
            return chats
        except APIError: raise
        except Exception as e:
            detail = str(e)
            logger.exception(f'[{cls._logs_tag}] Unknown exception | Detail: {detail}')
            raise UnknownError(detail) from e
    
    
    @classmethod
    async def load_timestamp(cls, start_timestamp: float | None = None, end_timestamp: float | None = None) -> dict:
        try:
            chats = {'chats': []}
            start_timestamp, end_timestamp = end_timestamp, start_timestamp
            
            response = await cls._get_chats(start_timestamp if not start_timestamp is None else None)
            updated_at = cls._get_updated_at(response)
            if updated_at is None:
                await cls._log_result(len(chats['chats']))
                return chats
            
            while end_timestamp is None or updated_at > end_timestamp:
                chats = cls._add_chats(response['data']['biz_data']['chat_sessions'], chats)
                
                has_more = cls._has_more_chats(response)
                if not has_more:
                    await cls._log_result(len(chats['chats']))
                    return chats
                
                updated_at = cls._get_updated_at(response)
                if updated_at is None:
                    await cls._log_result(len(chats['chats']))
                    return chats
                elif not end_timestamp is None and updated_at <= end_timestamp: break
                
                response = await cls._get_chats(updated_at)
            
            if not end_timestamp is None:
                for i, chat_session in enumerate(response['data']['biz_data']['chat_sessions']):
                    if chat_session['updated_at'] <= end_timestamp: break
                chats = cls._add_chats(response['data']['biz_data']['chat_sessions'][:i], chats)
            
            await cls._log_result(len(chats['chats']))
            return chats
        except APIError: raise
        except Exception as e:
            detail = str(e)
            logger.exception(f'[{cls._logs_tag}] Unknown exception | Detail: {detail}')
            raise UnknownError(detail) from e
    
    
    @classmethod
    async def delete_chats(cls, chat_ids: list[str]) -> None:
        try:
            async with AsyncSession() as session:
                response = await session.post(
                    f'{DATA.scheme}{DATA.authority}/api/v0/chat_session/delete', 
                    headers=DATA.headers, 
                    impersonate=DATA.impersonate, 
                    json={
                        'chat_session_ids': chat_ids
                    }
                )
            
            response = extract_from_response('Delete Chats', response)
            
            logger.info(f'[Delete Chats] Deleted {len(chat_ids)} chats')
            return None
        except APIError: raise
        except Exception as e:
            detail = str(e)
            logger.exception(f'[Delete Chats] Unknown exception | Detail: {detail}')
            raise UnknownError(detail) from e