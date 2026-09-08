from loguru import logger
from curl_cffi.requests import AsyncSession

from .data import DATA
from .utils import extract_from_response
from .exceptions import APIError, DeepSeekError, UnknownError



class Chat:
    @classmethod
    async def create(cls) -> dict:
        try:
            async with AsyncSession() as session:
                response = await session.post(
                    f'{DATA.scheme}{DATA.authority}/api/v0/chat_session/create', 
                    headers=DATA.headers, 
                    impersonate=DATA.impersonate
                )
                
                response = extract_from_response('Create Chat', response)
                
                chat_session = response['data']['biz_data']['chat_session']
                if not chat_session:
                    detail = 'Chat session is empty'
                    logger.error(f'[Create Chat] Not created | Detail: {detail}')
                    raise DeepSeekError(detail)
                
                chat_id = chat_session['id']
                inserted_at = chat_session['inserted_at']
                updated_at = chat_session['updated_at']
                model_type = chat_session['model_type']
                
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
                    'model_type': model_type, 
                    'messages': []
                }
        except APIError: raise
        except Exception as e:
            detail = str(e)
            logger.exception(f'[Create Chat] Unknown exception | Detail: {detail}')
            raise UnknownError(detail) from e
    
    
    @classmethod
    async def load(cls, chat_id: str) -> dict:
        try:
            async with AsyncSession() as session:
                response = await session.get(
                    f'{DATA.scheme}{DATA.authority}/api/v0/chat/history_messages?chat_session_id={chat_id}', 
                    headers=DATA.headers, 
                    impersonate=DATA.impersonate
                )
                
                response = extract_from_response('Get Chat', response)
                
                chat_session = response['data']['biz_data']['chat_session']
                if not chat_session:
                    detail = 'Chat session is empty'
                    logger.error(f'[Get Chat] Not created | Detail: {detail}')
                    raise DeepSeekError(detail)
                
                title = chat_session['title']
                inserted_at = chat_session['inserted_at']
                updated_at = chat_session['updated_at']
                current_message_id = chat_session['current_message_id']
                model_type = chat_session['model_type']
                messages = []
                
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
                    messages.append({
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
                
                logger.info(f'[Get chat] Retrieved | Chat ID: {chat_id}')
                return {
                    'chat_id': chat_id, 
                    'title': title, 
                    'inserted_at': inserted_at, 
                    'updated_at': updated_at, 
                    'current_message_id': current_message_id, 
                    'model_type': model_type, 
                    'messages': messages
                }
        except APIError: raise
        except Exception as e:
            detail = str(e)
            logger.exception(f'[Get Chat] Unknown exception | Detail: {detail}')
            raise UnknownError(detail) from e
    
    
    @classmethod
    async def update_title(cls, chat_id: str, new_title: str) -> dict:
        try:
            async with AsyncSession() as session:
                response = await session.post(
                    f'{DATA.scheme}{DATA.authority}/api/v0/chat_session/update_title', 
                    headers=DATA.headers, 
                    impersonate=DATA.impersonate, 
                    json={
                        'chat_session_id': chat_id, 
                        'title': new_title
                    }
                )
            
            response = extract_from_response('Chat Title', response)
            
            title = response['data']['biz_data']['title']
            
            logger.info(f'[Chat Title] Title changed | New title: {title}')
            return {
                'chat_id': chat_id, 
                'title': title
            }
        except APIError: raise
        except Exception as e:
            detail = str(e)
            logger.exception(f'[Chat Title] Unknown exception | Detail: {detail}')
            raise UnknownError(detail) from e