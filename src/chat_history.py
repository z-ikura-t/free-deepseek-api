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
    
    
    async def _chats_retrieved(self) -> None:
        if self._data.debug: logger.info(f'[Chat History] Retrieved {len(self.chats)} chats')
    
    
    async def _get_chats(self, updated_at: float | None = None) -> Response | None:
        async with AsyncSession() as session:
            response = await session.get(
                f'{self._data.scheme}{self._data.authority}/api/v0/chat_session/fetch_page', 
                headers=self._data.headers, 
                params={} if updated_at is None else {'lte_cursor.pinned': False, 'lte_cursor.updated_at': updated_at}, 
                timeout=10, 
                impersonate=self._data.impersonate
            )
        
        response = await extract_from_response('Chat History', response, debug=self._data.debug)
        if not response[0]:
            self.exception_detail = response[1]
            return None
        else: response = response[1]
        return response
    
    
    async def _has_more_chats(self, response: Response) -> bool:
        has_more = response['data']['biz_data']['has_more']
        if not has_more:
            await self._chats_retrieved()
            return False
        return True
    
    
    async def _process_response(self, response: Response, add: bool = False) -> Response | None:
        if response is None: return None
        
        if add: await self._add_chats(response['data']['biz_data']['chat_sessions'])
        
        has_more = await self._has_more_chats(response)
        if not has_more: return None
        
        if not response['data']['biz_data']['chat_sessions']:
            await self._chats_retrieved()
            return None
        updated_at = response['data']['biz_data']['chat_sessions'][-1]['updated_at']
        response = await self._get_chats(updated_at)
        return response
    
    
    async def _add_chats(self, chat_sessions: list[dict]) -> None:
        for chat_session in chat_sessions:
            self.chats.append({
            'chat_id': chat_session['id'], 
            'title': chat_session['title'], 
            'model_type': chat_session['model_type'], 
            'updated_at': chat_session['updated_at']
        })
    
    
    async def fetch(self, start: int = 0, end: int = 100) -> None:
        try:
            cursor_chats_count = 100
            response = await self._get_chats()
            if response is None: return None
            if not response['data']['biz_data']['chat_sessions']:
                await self._chats_retrieved()
                return None
            updated_at = response['data']['biz_data']['chat_sessions'][-1]['updated_at']
            for _ in range(start // cursor_chats_count):
                response = await self._process_response(response)
                if response is None: return None
            
            chats_count = end - start
            
            if len(response['data']['biz_data']['chat_sessions']) <= start % cursor_chats_count:
                await self._chats_retrieved()
                return None
            last_chat = response['data']['biz_data']['chat_sessions'][start % cursor_chats_count]
            if last_chat: updated_at = last_chat['updated_at']
            else:
                await self._chats_retrieved()
                return None
            response = await self._get_chats(updated_at)
            for _ in range(chats_count // cursor_chats_count):
                response = await self._process_response(response, add=True)
                if response is None: return None
            
            has_more = await self._has_more_chats(response)
            if not has_more: return None
            
            k = chats_count % 100
            await self._add_chats(response['data']['biz_data']['chat_sessions'][:k])
            
            await self._chats_retrieved()
        except Exception as e:
            self.exception_detail = str(e)
            if self._data.debug: logger.error(f'[Chat History] Unknown exception | Detail: {self.exception_detail}')
            print_exc()