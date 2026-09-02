from loguru import logger
from traceback import print_exc
from curl_cffi.requests import AsyncSession, Response

from .data import Data
from .utils import extract_from_response



class ChatHistory:
    def __init__(self, data: Data):
        self._data = data
        
        self.exception_detail = None
        
        self.chats = []
    
    
    async def _get_chats(self, updated_at: float | None = None) -> Response | None:
        async with AsyncSession() as session:
            response = await session.get(
                f'{self._data.scheme}{self._data.authority}/api/v0/chat_session/fetch_page', 
                headers=self._data.headers, 
                params={} if updated_at is None else {'lte_cursor.pinned': False, 'lte_cursor.updated_at': updated_at}, 
                impersonate=self._data.impersonate, 
                timeout=10
            )
        
        response = extract_from_response('Chat History', response, debug=self._data.debug)
        if not response[0]:
            self.exception_detail = response[1]
            return None
        else: response = response[1]
        return response
    
    
    def _chats_retrieved(self) -> None:
        if self._data.debug: logger.info(f'[Chat History] Retrieved {len(self.chats)} chats')
    
    
    def _has_more_chats(self, response: Response) -> bool:
        has_more = response['data']['biz_data']['has_more']
        if not has_more:
            self._chats_retrieved()
            return False
        return True
    
    
    def _add_chats(self, chat_sessions: list[dict]) -> None:
        for chat_session in chat_sessions:
            self.chats.append({
            'chat_id': chat_session['id'], 
            'title': chat_session['title'], 
            'model_type': chat_session['model_type'], 
            'updated_at': chat_session['updated_at']
        })
    
    
    def _get_updated_at(self, response: Response) -> float | None:
        if not response['data']['biz_data']['chat_sessions']:
            self._chats_retrieved()
            return None
        updated_at = response['data']['biz_data']['chat_sessions'][-1]['updated_at']
        return updated_at
    
    
    async def _process_response(self, response: Response, add: bool = False) -> Response | None:
        if add: self._add_chats(response['data']['biz_data']['chat_sessions'])
        
        has_more = self._has_more_chats(response)
        if not has_more: return None
        
        updated_at = self._get_updated_at(response)
        if updated_at is None: return None
        
        response = await self._get_chats(updated_at)
        if response is None: return None
        
        return response
    
    
    async def _fetch_range(self, start: int = 0, end: int | None = None) -> None:
        cursor_chats_count = 100
        response = await self._get_chats()
        if response is None: return None
        updated_at = self._get_updated_at(response)
        if updated_at is None: return None
        
        for _ in range(start // cursor_chats_count):
            response = await self._process_response(response)
            if response is None: return None
        
        if len(response['data']['biz_data']['chat_sessions']) <= start % cursor_chats_count:
            self._chats_retrieved()
            return None
        last_chat = response['data']['biz_data']['chat_sessions'][start % cursor_chats_count]
        if last_chat: updated_at = last_chat['updated_at']
        else:
            self._chats_retrieved()
            return None
        response = await self._get_chats(updated_at)
        if response is None: return None
        
        if not end is None:
            chats_count = end - start
            for _ in range(chats_count // cursor_chats_count):
                response = await self._process_response(response, add=True)
                if response is None: return None
            
            has_more = self._has_more_chats(response)
            if not has_more: return None
            
            k = chats_count % 100
            self._add_chats(response['data']['biz_data']['chat_sessions'][:k])
        else:
            while True:
                response = await self._process_response(response, add=True)
                if response is None: return None
        
        self._chats_retrieved()
    
    
    async def _fetch_timestamp(self, start_timestamp: float | None = None, end_timestamp: float | None = None) -> None:
        start_timestamp, end_timestamp = end_timestamp, start_timestamp
        
        response = await self._get_chats(start_timestamp if not start_timestamp is None else None)
        if response is None: return None
        updated_at = self._get_updated_at(response)
        if updated_at is None: return None
        
        while end_timestamp is None or updated_at > end_timestamp:
            self._add_chats(response['data']['biz_data']['chat_sessions'])
            has_more = self._has_more_chats(response)
            if not has_more: return None
            updated_at = self._get_updated_at(response)
            if updated_at is None: return None
            elif not end_timestamp is None and updated_at <= end_timestamp: break
            response = await self._get_chats(updated_at)
            if response is None: return None
        if not end_timestamp is None:
            for i, chat_session in enumerate(response['data']['biz_data']['chat_sessions']):
                if chat_session['updated_at'] <= end_timestamp: break
            self._add_chats(response['data']['biz_data']['chat_sessions'][:i])
        self._chats_retrieved()
    
    
    async def fetch(self, start: int | float | None = 0, end: int | float | None = 100) -> None:
        try:
            if isinstance(start, int):
                response = await self._fetch_range(start, end)
                if response is None: return None
            else:
                response = await self._fetch_timestamp(start, end)
                if response is None: return None
        except Exception as e:
            self.exception_detail = str(e)
            if self._data.debug: logger.error(f'[Chat History] Unknown exception | Detail: {self.exception_detail}')
            print_exc()
    
    
    async def delete_chats(self, chat_ids: list[str]) -> None:
        try:
            async with AsyncSession() as session:
                response = await session.post(
                    f'{self._data.scheme}{self._data.authority}/api/v0/chat_session/delete', 
                    headers=self._data.headers, 
                    impersonate=self._data.impersonate, 
                    json={
                        'chat_session_ids': chat_ids
                    }
                )
            
            response = extract_from_response('Chats Delete', response, debug=self._data.debug)
            if not response[0]:
                self.exception_detail = response[1]
                return None
            
            if self._data.debug: logger.info(f'[Chats Delete] Deleted {len(chat_ids)} chats')
        except Exception as e:
            self.exception_detail = str(e)
            if self._data.debug: logger.error(f'[Chats Delete] Unknown exception | Detail: {self.exception_detail}')
            print_exc()