from loguru import logger
from curl_cffi.requests import AsyncSession

from . import settings
from .utils import extract_from_response, handle_exceptions
from .exceptions import DeepSeekError, DeepSeekResponseError



class Chat:
    @classmethod
    @handle_exceptions(log_tag='Create Chat')
    async def create(cls, ds_session: AsyncSession) -> dict:
        response = await ds_session.post(
            f'{settings.DEEPSEEK_URL}/chat_session/create', 
            headers=settings.HEADERS
        )
        
        response = extract_from_response('Create Chat', response)
        
        biz_data = response['data'].get('biz_data')
        if biz_data is None: raise DeepSeekResponseError()
        chat_session = biz_data.get('chat_session')
        if chat_session is None: raise DeepSeekResponseError()
        
        if not chat_session:
            detail = 'Chat session is empty'
            logger.error(f'[Create Chat] Not created | Detail: {detail}')
            raise DeepSeekError(detail)
        
        chat_id = chat_session.get('id')
        inserted_at = chat_session.get('inserted_at')
        updated_at = chat_session.get('updated_at')
        if chat_id is None or inserted_at is None or updated_at is None: raise DeepSeekResponseError()
        
        if not chat_id:
            detail = 'Chat ID is empty'
            logger.error(f'[Create Chat] Not created | Detail: {detail}')
            raise DeepSeekError(detail)
        
        logger.info(f'[Create Chat] Created | Chat ID: {chat_id}')
        return {
            'chat_id': chat_id, 
            'title': None, 
            'inserted_at': inserted_at, 
            'updated_at': updated_at, 
            'current_message_id': None, 
            'messages': []
        }
    
    
    @classmethod
    @handle_exceptions(log_tag='Load Chat')
    async def load(cls, ds_session: AsyncSession, chat_id: str) -> dict:
        response = await ds_session.get(
            f'{settings.DEEPSEEK_URL}/chat/history_messages?chat_session_id={chat_id}', 
            headers=settings.HEADERS, 
        )
        
        response = extract_from_response('Load Chat', response)
        
        biz_data = response['data'].get('biz_data')
        if biz_data is None: raise DeepSeekResponseError()
        chat_session = biz_data.get('chat_session')
        if chat_session is None: raise DeepSeekResponseError()
        
        if not chat_session:
            detail = 'Chat session is empty'
            logger.error(f'[Load Chat] Not created | Detail: {detail}')
            raise DeepSeekError(detail)
        
        title = chat_session.get('title', False)
        inserted_at = chat_session.get('inserted_at')
        updated_at = chat_session.get('updated_at')
        current_message_id = chat_session.get('current_message_id', 'None')
        if title is False or inserted_at is None or updated_at is None or current_message_id == 'None': raise DeepSeekResponseError()
        messages = []
        
        chat_messages = response['data']['biz_data'].get('chat_messages')
        if chat_messages is None: raise DeepSeekResponseError()
        for chat_message in chat_messages:
            message_files = []
            message_think = None
            message_content = ''
            message_fragments = chat_message.get('fragments')
            if message_fragments is None: raise DeepSeekResponseError()
            
            for fragment in message_fragments:
                fragment_type = fragment.get('type')
                if fragment_type is None: raise DeepSeekResponseError()
                
                if fragment_type == 'FILE':
                    fragment_files = fragment.get('files')
                    if fragment_files is None: raise DeepSeekResponseError()
                    
                    for message_file in fragment_files:
                        file_id = message_file.get('id')
                        file_name = message_file.get('file_name')
                        file_size = message_file.get('file_size')
                        message_files.append({
                            'file_id': file_id, 
                            'name': file_name, 
                            'size': file_size
                        })
                elif fragment_type in ('THINK', 'REQUEST', 'RESPONSE'):
                    fragment_content = fragment.get('content')
                    if fragment_content is None: raise DeepSeekResponseError()
                    if fragment_type == 'THINK': message_think = fragment_content
                    elif fragment_type in ('REQUEST', 'RESPONSE'): message_content = fragment_content
            
            message_id = chat_message.get('message_id')
            parent_message_id = chat_message.get('parent_id', 'None')
            message_role = chat_message.get('role')
            if message_id is None or parent_message_id == 'None' or message_role is None: raise DeepSeekResponseError()
            messages.append({
                'message_id': message_id, 
                'parent_message_id': parent_message_id, 
                'role': message_role, 
                'think': message_think, 
                'content': message_content, 
                'files': message_files
            })
        
        logger.info(f'[Load chat] Loaded | Chat ID: {chat_id}')
        return {
            'chat_id': chat_id, 
            'title': title, 
            'inserted_at': inserted_at, 
            'updated_at': updated_at, 
            'current_message_id': current_message_id, 
            'messages': messages
         }
    
    
    @classmethod
    @handle_exceptions(log_tag='Change Chat Title')
    async def update_title(cls, ds_session: AsyncSession, chat_id: str, new_title: str) -> dict:
        response = await ds_session.post(
            f'{settings.DEEPSEEK_URL}/chat_session/update_title', 
            headers=settings.HEADERS, 
            json={
                'chat_session_id': chat_id, 
                'title': new_title
            }
        )
        
        response = extract_from_response('Change Chat Title', response)
        
        biz_data = response['data'].get('biz_data')
        if biz_data is None: raise DeepSeekResponseError()
        title = biz_data.get('title')
        if title is None: raise DeepSeekResponseError()
        
        logger.info(f'[Change Chat Title] Title changed | Chat ID: {chat_id}, New title: {title}')
        return {
            'chat_id': chat_id, 
            'title': title
        }