from loguru import logger
from traceback import print_exc
from curl_cffi.requests import AsyncSession

from .data import Data
from .utils import extract_from_response



class Chat:
    def __init__(self, data: Data):
        self._data = data
        
        self.exception_detail = None
        
        self.chat_id = None
        self.title = None
        self.inserted_at = None
        self.updated_at = None
        self.current_message_id = None
        self.model_type = None
        self.messages = []
    
    
    async def fetch(self, chat_id: str | None=None) -> None:
        try:
            self.chat_id = chat_id
            if not chat_id is None:
                async with AsyncSession() as session:
                    response = await session.get(
                        f'{self._data.scheme}{self._data.authority}/api/v0/chat/history_messages?chat_session_id={self.chat_id}', 
                        headers=self._data.headers, 
                        impersonate=self._data.impersonate
                    )
                
                response = await extract_from_response('Chat', response, debug=self._data.debug)
                if not response[0]:
                    self.exception_detail = response[1]
                    return None
                else: response = response[1]
                
                self.title = response['data']['biz_data']['chat_session']['title']
                self.inserted_at = response['data']['biz_data']['chat_session']['inserted_at']
                self.updated_at = response['data']['biz_data']['chat_session']['updated_at']
                self.current_message_id = response['data']['biz_data']['chat_session']['current_message_id']
                self.model_type = response['data']['biz_data']['chat_session']['model_type']
                
                chat_messages = response['data']['biz_data']['chat_messages']
                for chat_message in chat_messages:
                    message_files = []
                    message_think = None
                    message_content = ''
                    for fragment in chat_message['fragments']:
                        if fragment['type'] == 'FILE':
                            for message_file in fragment['files']:
                                message_files.append(message_file)
                        elif fragment['type'] == 'THINK':
                            message_think = fragment['content']
                        elif fragment['type'] in ('REQUEST', 'RESPONSE'):
                            message_content = fragment['content']
                    self.messages.append({
                        'message_id': chat_message['message_id'], 
                        'parent_message_id': chat_message['parent_id'], 
                        'role': chat_message['role'], 
                        'think': message_think, 
                        'content': message_content, 
                        'files': [{
                            'file_id': message_file['id'], 
                            'name': message_file['file_name'], 
                            'size': message_file['file_size'], 
                        } for message_file in message_files]
                    })
                
                if self._data.debug: logger.info(f'[Chat] Retrieved | Chat ID: {self.chat_id}')
            else:
                async with AsyncSession() as session:
                    response = await session.post(
                        f'{self._data.scheme}{self._data.authority}/api/v0/chat_session/create', 
                        headers = self._data.headers, 
                        impersonate=self._data.impersonate
                    )
                    
                    response = await extract_from_response('Chat', response, debug=self._data.debug)
                    if not response[0]:
                        self.exception_detail = response[1]
                        return None
                    else: response = response[1]
                    
                    self.chat_id = response['data']['biz_data']['chat_session']['id']
                    self.title = None
                    self.inserted_at = response['data']['biz_data']['chat_session']['inserted_at']
                    self.updated_at = response['data']['biz_data']['chat_session']['updated_at']
                    self.current_message_id = None
                    self.model_type = response['data']['biz_data']['chat_session']['model_type']
                    self.messages = []
                    
                    if not self.chat_id:
                        self.exception_detail = 'chat ID is empty'
                        if self._data.debug: logger.info(f'[Chat] Not created | Detail: {self.exception_detail}')
                        return None
                    if self._data.debug: logger.info(f'[Chat] Created | Chat ID: {self.chat_id}')
        except Exception as e:
            self.exception_detail = str(e)
            if self._data.debug: logger.error(f'[Chat] Unknown exception | Detail: {self.exception_detail}')
            print_exc()
    
    
    async def update_title(self, chat_id: str, new_title: str) -> None:
        try:
            self.chat_id = chat_id
            
            async with AsyncSession() as session:
                response = await session.post(
                    f'{self._data.scheme}{self._data.authority}/api/v0/chat_session/update_title', 
                    headers=self._data.headers, 
                    impersonate=self._data.impersonate, 
                    json={
                        'chat_session_id': self.chat_id, 
                        'title': new_title
                    }
                )
            
            response = await extract_from_response('Chat Title', response, debug=self._data.debug)
            if not response[0]:
                self.exception_detail = response[1]
                return None
            else: response = response[1]
            
            self.title = response['data']['biz_data']['title']
            
            if self._data.debug: logger.info(f'[Chat Title] Title changed | New title: {self.title}')
        except Exception as e:
            self.exception_detail = str(e)
            if self._data.debug: logger.error(f'[Chat Title] Unknown exception | Detail: {self.exception_detail}')
            print_exc()