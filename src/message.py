import json
from loguru import logger
from json import JSONDecodeError

from curl_cffi.requests import AsyncSession

from . import settings
from .pow_challenge.pow_challenge import POWChallenge
from .exceptions import APIError, DeepSeekResponseError, DeepSeekSSEError, UnknownError



class Message:
    _logs_tag = 'Message'
    
    _event_files_type = 'FILES'
    _event_session_type = 'SESSION'
    _event_message_data_type = 'MESSAGE_DATA'
    
    # _content_think_type = 'THINK'
    _content_response_type = 'RESPONSE'
    
    
    @classmethod
    async def _solve_pow_challenge(cls) -> str:
        x_ds_pow_response = await POWChallenge.solve(f'{settings.API}/chat/completion')
        return x_ds_pow_response['result']
    
    
    @classmethod
    async def _get_request_data(cls, chat_id: str, parent_message_id: int | None, prompt: str, file_ids: list[str] | None = None) -> tuple[dict, dict]:
        x_ds_pow_response_result = await cls._solve_pow_challenge()
        
        headers = settings.HEADERS.copy()
        headers['x-ds-pow-response'] = x_ds_pow_response_result
        ref_file_ids = file_ids or []
        
        request_json = {
            'chat_session_id': chat_id, 
            'parent_message_id': parent_message_id, 
            'preempt': False, 
            'prompt': prompt, 
            'ref_file_ids': ref_file_ids, 
            'search_enabled': settings.DEEPSEEK_SEARCH_ENABLED, 
            'thinking_enabled': settings.DEEPSEEK_THINKING_ENABLED
        }
        
        return headers, request_json
    
    
    @classmethod
    def _check_sse_response_status(cls, status: str) -> None:
        if status != 'event: ready':
            try:
                status = json.loads(status)
                detail = status['data']['biz_msg']
            except JSONDecodeError:
                detail = status
            logger.error(f'[{cls._logs_tag}] SSE exception | Detail: {detail}')
            raise DeepSeekSSEError(detail)
    
    
    @classmethod
    def _parse_sse_message(cls, sse_message_content_type: str, sse_message: str) -> tuple[str, str, dict]:
        data = json.loads(sse_message[6:])
        
        sse_message_content = ''
        sse_message_data = {}
        if not data.get('p') is None:
            if data.get('p') == 'response' and data.get('v'):
                if isinstance(data['v'][0]['v'], list) and not data['v'][0]['v'][0].get('content') is None:
                    sse_message_content_type = data['v'][0]['v'][0]['type']
                    sse_message_content = data['v'][0]['v'][0]['content']
            elif data.get('p') == 'response/fragments' and data.get('v'):
                sse_message_content_type = data['v'][0]['type']
                sse_message_content = data['v'][0]['content']
            elif data.get('p') == 'response/fragments/-1' and data.get('v'): sse_message_content = data['v'][0]['v']
            elif data.get('p') == 'response/fragments/-1/content' and data.get('v'): sse_message_content = data['v']
        elif not data.get('v') is None:
            if isinstance(data['v'], str): sse_message_content = data['v']
            elif isinstance(data['v'], list): sse_message_content = data['v'][0]['v']
            elif isinstance(data['v'], dict):
                message_data = data['v']['response']
                
                sse_message_data = {
                    'message_id': message_data['message_id'], 
                    'parent_message_id': message_data['parent_id'], 
                    'role': message_data['role']
                }
                
                sse_message_content_type = message_data['fragments'][0]['type']
                sse_message_content = message_data['fragments'][0]['content']
        
        return sse_message_content_type, sse_message_content, sse_message_data
    
    
    @classmethod
    def _process_sse_message(cls, sse_message_event_type: str, sse_message_content_type: str, sse_message: str) -> tuple[str, str, dict]:
        data = json.loads(sse_message[6:])
        
        sse_message_content = ''
        sse_message_data = {}
        if sse_message_event_type == cls._event_files_type:
            sse_message_content = {
                'file_id': data['id'], 
                'name': data['file_name'], 
                'size': data['file_size']
            }
        elif sse_message_event_type == cls._event_session_type:
            sse_message_content_type, sse_message_content, sse_message_data = cls._parse_sse_message(sse_message_content_type, sse_message)
        
        return sse_message_content_type, sse_message_content, sse_message_data
    
    
    @classmethod
    async def _read_event_stream(cls, request_data: tuple):
        async with AsyncSession() as session:
            response = await session.post(
                f'{settings.DEEPSEEK_URL}/chat/completion', 
                impersonate=settings.IMPERSONATE, 
                headers=request_data[0], 
                json=request_data[1], 
                stream=True
            )
            
            lines = response.aiter_lines()
            status = await anext(lines)
            cls._check_sse_response_status(status.decode('utf-8'))
            
            event_type, content_type = '', ''
            async for line in lines:
                if not line: continue
                line = line.decode('utf-8')
                
                if line.startswith('event: '):
                    if line == 'event: update_file':
                        event_type = cls._event_files_type
                    elif line == 'event: update_session':
                        event_type = cls._event_session_type
                    elif line == 'event: close': break
                elif line.startswith('data: '):
                    new_content_type, fragment, new_message_data = cls._process_sse_message(event_type, content_type, line)
                    content_type = new_content_type
                    
                    if new_message_data:
                        if new_message_data.get('message_id') is None: raise DeepSeekResponseError('Message ID not found')
                        
                        yield {
                            'event_type': cls._event_message_data_type, 
                            'content': new_message_data
                        }
                    
                    if fragment:
                        yield {
                            'event_type': event_type, 
                            'content_type': content_type, 
                            'content': fragment
                        }
    
    
    @classmethod
    async def completion(cls, chat_id: str, parent_message_id: int | None, prompt: str, file_ids: list[str] | None = None) -> dict:
        try:
            request_data = await cls._get_request_data(chat_id, parent_message_id, prompt, file_ids=file_ids)
            
            message_data = {}
            files = []
            think_text = []
            response_text = []
            async for chunk in cls._read_event_stream(request_data):
                if chunk['event_type'] == cls._event_files_type:
                    files.append(chunk['content'])
                elif chunk['event_type'] == cls._event_message_data_type:
                    message_data = {
                        'message_id': chunk['content']['message_id'], 
                        'parent_message_id': chunk['content']['parent_message_id'], 
                        'role': chunk['content']['role']
                    }
                elif chunk['event_type'] == cls._event_session_type:
                    if chunk['content_type'] == cls._content_response_type:
                        response_text.append(chunk['content'])
                    else:
                        think_text.append(chunk['content'])
            if message_data.get('message_id') is None: raise DeepSeekResponseError('Message ID not found')
            
            if not think_text: think_text = None
            else: think_text = ''.join(think_text)
            
            if not response_text: raise DeepSeekResponseError('Empty response')
            else: response_text = ''.join(response_text)
            
            logger.info(f'[{cls._logs_tag}] Generated | Output: {response_text[:30]}...')
            
            return {
                'user': {
                    'message_id': message_data['parent_message_id'], 
                    'parent_message_id': parent_message_id, 
                    'role': 'USER', 
                    'content': prompt, 
                    'files': files
                }, 
                'assistant': {
                    'message_id': message_data['message_id'], 
                    'parent_message_id': message_data['parent_message_id'], 
                    'role': 'ASSISTANT', 
                    'think': think_text, 
                    'content': response_text, 
                }
            }
        except APIError: raise
        except Exception as e:
            detail = str(e)
            logger.exception(f'[{cls._logs_tag}] Unknown exception | Detail: {detail}')
            raise UnknownError(detail) from e
    
    
    @classmethod
    async def completion_stream(cls, chat_id: str, parent_message_id: int | None, prompt: str, file_ids: list[str] | None = None):
        try:
            request_data = await cls._get_request_data(chat_id, parent_message_id, prompt, file_ids=file_ids)
            
            yield 'event: ready\n'
            logger.info(f'[{cls._logs_tag}] Event ready')
            
            current_type = None
            async for chunk in cls._read_event_stream(request_data):
                if chunk['event_type'] == cls._event_files_type:
                    if current_type != chunk['event_type']:
                        yield 'event: update_files\n'
                        current_type = chunk['event_type']
                    
                    yield f'data: {json.dumps({
                        'type': 'file', 
                        **chunk['content']
                    }, ensure_ascii=False)}\n\n'
                elif chunk['event_type'] == cls._event_message_data_type:
                    if current_type != chunk['event_type']:
                        yield 'event: update_message_data\n'
                        current_type = chunk['event_type']
                    
                    user_message = {
                        'type': 'message_data', 
                        'message_id': chunk['content']['parent_message_id'], 
                        'parent_message_id': parent_message_id, 
                        'role': 'USER'
                    }
                    yield f'data: {json.dumps(user_message)}\n\n'
                    assistant_message = {
                        'type': 'message_data', 
                        'message_id': chunk['content']['message_id'], 
                        'parent_message_id': chunk['content']['parent_message_id'], 
                        'role': 'ASSISTANT'
                    }
                    yield f'data: {json.dumps(assistant_message)}\n\n'
                elif chunk['event_type'] == cls._event_session_type:
                    if current_type != chunk['event_type']:
                        yield 'event: update_session\n'
                        current_type = chunk['event_type']
                    
                    content_type = 'response' if chunk['content_type'] == cls._content_response_type else 'think'
                    yield f'data: {json.dumps({
                        'type': content_type, 
                        'content': chunk['content']
                    }, ensure_ascii=False)}\n\n'
            
            yield 'event: close\n\n'
            logger.info(f'[{cls._logs_tag}] Event close')
        except Exception as e:
            detail = str(e)
            if isinstance(e, UnknownError): logger.exception(f'[{cls._logs_tag}] Unknown exception | Detail: {detail}')
            yield 'event: error\n'
            yield f'data: {json.dumps({"error": detail})}\n\n'
            yield 'event: close\n\n'