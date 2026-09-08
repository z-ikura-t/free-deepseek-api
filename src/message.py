import json
from loguru import logger
from json import JSONDecodeError

from curl_cffi.requests import AsyncSession

from .data import DATA, CONFIG
from .pow_challenge import POWChallenge
from .exceptions import APIError, DeepSeekResponseError, DeepSeekSSEError, UnknownError



class Message:
    _logs_tag = 'Message'
    
    _event_files_type = 'FILES'
    _event_session_type = 'SESSION'
    
    
    @classmethod
    async def _solve_pow_challenge(cls) -> str:
        x_ds_pow_response = await POWChallenge.solve('/api/v0/chat/completion')
        return x_ds_pow_response['result']
    
    
    @classmethod
    async def _get_request_data(cls, chat_id: str, parent_message_id: int, prompt: str, file_ids: list[str] | None = None) -> tuple[dict, dict]:
        x_ds_pow_response_result = await cls._solve_pow_challenge()
        
        headers = DATA.headers.copy()
        headers['x-ds-pow-response'] = x_ds_pow_response_result
        ref_file_ids = file_ids or []
        
        if CONFIG.base_prompt_enabled: prompt = f'{CONFIG.base_prompt}\n{prompt}'       
        
        request_json = {
            'chat_session_id': chat_id, 
            'parent_message_id': parent_message_id, 
            'model_type': CONFIG.model, 
            'preempt': False, 
            'prompt': prompt, 
            'ref_file_ids': ref_file_ids, 
            'search_enabled': CONFIG.search_enabled if CONFIG.model == 'default' else False, 
            'thinking_enabled': CONFIG.thinking_enabled
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
    def _process_sse_message(cls, sse_message_event_type: str, sse_message_content_type: str, sse_message: str, stream: bool = False) -> tuple[str, str, dict]:
        data = json.loads(sse_message[6:])
        
        sse_message_content = ''
        sse_message_data = {}
        if sse_message_event_type == cls._event_files_type:
            sse_message_content = {
                'file_id': data['id'], 
                'name': data['file_name'], 
                'size': data['file_size']
            }
            if stream: sse_message_content = json.dumps(sse_message_content)
        elif sse_message_event_type == cls._event_session_type:
            sse_message_content_type, sse_message_content, sse_message_data = cls._parse_sse_message(sse_message_content_type, sse_message)
            if stream and sse_message_content: sse_message_content = json.dumps({'content': sse_message_content})
        
        if stream: sse_message_content = f'data: {sse_message_content}\n\n' if sse_message_content else ''
        return sse_message_content_type, sse_message_content, sse_message_data
    
    
    @classmethod
    async def generate_json(cls, chat_id: str, parent_message_id: int, prompt: str, file_ids: list[str] | None = None) -> dict:
        try:
            request_data = await cls._get_request_data(chat_id, parent_message_id, prompt, file_ids=file_ids)
            
            async with AsyncSession() as session:
                response = await session.post(
                    f'{DATA.scheme}{DATA.authority}/api/v0/chat/completion', 
                    impersonate=DATA.impersonate, 
                    headers=request_data[0], 
                    json=request_data[1], 
                    stream=False
                )
            
            if response.status_code == 200:
                lines = response.text.split('\n')
                if not lines: raise DeepSeekResponseError('Empty response')
                
                status = cls._check_sse_response_status(lines[0])
                
                i = 1
                think, content, files = [], [], []
                event_type, content_type = '', ''
                message_data = {
                    'message_id': None, 
                    'parent_message_id': None, 
                    'role': 'ASSISTANT'
                }
                while i < len(lines) and lines[i] != 'event: close':
                    line = lines[i]
                    if not line: i += 1; continue
                    
                    if line.startswith('event: '):
                        if line == 'event: update_file':
                            event_type = cls._event_files_type
                        elif line == 'event: update_session':
                            event_type = cls._event_session_type
                    elif line.startswith('data: '):
                        content_type, fragment, new_message_data = cls._process_sse_message(event_type, content_type, line, stream=False)
                        if new_message_data: message_data = new_message_data
                        if event_type == cls._event_files_type:
                            files.append(fragment)
                        elif event_type == cls._event_session_type:
                            if not fragment: i += 1; continue
                            if content_type == 'RESPONSE': content.append(fragment)
                            else: think.append(fragment)
                    i += 1
                if not think: think = None
                else: think = ''.join(think)
                
                if not content: raise DeepSeekResponseError('Empty response')
                else: content = ''.join(content)
                
                if message_data.get('message_id') is None: raise DeepSeekResponseError('Message data not found')
                
                logger.info(f'[{cls._logs_tag}] Output: {content[:30]}...')
                return {
                    'message_id': message_data['message_id'], 
                    'parent_message_id': message_data['parent_message_id'], 
                    'role': 'ASSISTANT', 
                    'think': think, 
                    'content': content, 
                    'files': files
                }
            else:
                detail = response.text[:100]
                logger.error(f'[{cls._logs_tag}] Response exception | Detail: {detail}')
                raise DeepSeekResponseError(detail)
        except APIError: raise
        except Exception as e:
            detail = str(e)
            logger.exception(f'[{cls._logs_tag}] Unknown exception | Detail: {detail}')
            raise UnknownError(detail) from e
    
    
    @classmethod
    async def generate_stream(cls, chat_id: str, parent_message_id: int, prompt: str, file_ids: list[str] | None = None):
        try:
            request_data = await cls._get_request_data(chat_id, parent_message_id, prompt, file_ids=file_ids)
            
            async with AsyncSession() as session:
                response = await session.post(
                    f'{DATA.scheme}{DATA.authority}/api/v0/chat/completion', 
                    impersonate=DATA.impersonate, 
                    headers=request_data[0], 
                    json=request_data[1], 
                    stream=True
                )
                
                lines = response.aiter_lines()
                status = await anext(lines)
                status = cls._check_sse_response_status(status.decode('utf-8'))
                
                yield 'event: ready\n'
                logger.info(f'[{cls._logs_tag}] Event ready')
                
                event_type, content_type = '', ''
                message_data = {
                    'message_id': None, 
                    'parent_message_id': None, 
                    'role': 'ASSISTANT'
                }
                async for line in lines:
                    if not line: continue
                    line = line.decode('utf-8')
                    
                    if line.startswith('event: '):
                        if line == 'event: update_file':
                            if event_type != cls._event_files_type:
                                yield 'event: update_files\n'
                            event_type = cls._event_files_type
                        elif line == 'event: update_session':
                            event_type = cls._event_session_type
                        elif line == 'event: close': break
                    elif line.startswith('data: '):
                        new_content_type, fragment, new_message_data = cls._process_sse_message(event_type, content_type, line, stream=True)
                        if new_content_type != content_type:
                            if event_type == cls._event_session_type:
                                yield 'event: update_session\n'
                                yield f'data: {json.dumps({"type": new_content_type})}\n\n'
                        content_type = new_content_type
                        
                        if new_message_data: message_data = new_message_data
                        
                        if fragment:
                            yield fragment
                
                if message_data.get('message_id') is None: raise DeepSeekResponseError('Message data not found')
                
                yield 'event: messages_data\n'
                yield f'data: {json.dumps({
                    "message_id": message_data['parent_message_id'],
                    "parent_message_id": parent_message_id,
                    "role": "USER"
                })}\n\n'
                yield f'data: {json.dumps({
                    "message_id": message_data['message_id'],
                    "parent_message_id": message_data['parent_message_id'],
                    "role": "ASSISTANT"
                })}\n\n'
                
                yield 'event: close\n\n'
                logger.info(f'[{cls._logs_tag}] Event close')
        except Exception as e:
            detail = str(e)
            if isinstance(e, UnknownError): logger.exception(f'[{cls._logs_tag}] Unknown exception | Detail: {detail}')
            yield 'event: error\n'
            yield f'data: {json.dumps({"error": detail})}\n\n'
            yield 'event: close\n\n'