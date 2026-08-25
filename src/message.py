import json
from loguru import logger
from traceback import print_exc
from curl_cffi.requests import AsyncSession

from .data import Data, Config
from .pow_challenge import POWChallenge



class Message:
    def __init__(self, data: Data):
        self._data = data
        
        self.exception_detail = None
        
        self.message_id = None
        self.parent_message_id = None
        self.role = None
        self.think = None
        self.content = None
        self.files = []
        
        self.event_files_type = 'FILES'
        self.event_session_type = 'SESSION'
    
    
    async def _solve_pow_challenge(self) -> str | None:
        x_ds_pow_response = POWChallenge(self._data)
        await x_ds_pow_response.fetch('/api/v0/chat/completion')
        if not x_ds_pow_response.exception_detail is None:
            self.exception_detail = x_ds_pow_response.exception_detail
            return None
        return x_ds_pow_response.result
    
    
    async def _get_request_data(self, config: Config, chat_id: str, parent_message_id: int, prompt: str, file_ids: list[str] | None = None) -> tuple[dict, dict] | None:
        x_ds_pow_response_result = await self._solve_pow_challenge()
        if x_ds_pow_response_result is None: return None
        
        headers = self._data.headers.copy()
        headers['x-ds-pow-response'] = x_ds_pow_response_result
        ref_file_ids = file_ids or []
        
        request_json = {
            'chat_session_id': chat_id, 
            'parent_message_id': parent_message_id, 
            'model_type': config.model, 
            'preempt': False, 
            'prompt': prompt, 
            'ref_file_ids': ref_file_ids, 
            'search_enabled': config.search_enabled if config.model == 'default' else False, 
            'thinking_enabled': config.thinking_enabled
        }
        
        return headers, request_json
    
    
    def _check_sse_response_status(self, status: str) -> bool:
        if status != 'event: ready':
            try:
                status = json.loads(event_status)
                self.exception_detail = status['data']['biz_msg']
            except:
                self.exception_detail = status
            if self._data.debug: logger.error(f'[Message] SSE exception | Detail: {self.exception_detail}')
            return False
        return True
    
    
    def _parse_sse_message(self, sse_message_content_type: str, sse_message: str) -> tuple[str, str]:
        data = json.loads(sse_message[6:])
        
        sse_message_content = ''
        if not data.get('p') is None:
            if data.get('p') == 'response' and data.get('v'):
                if type(data['v'][0]['v']) == list and not data['v'][0]['v'][0].get('content') is None:
                    sse_message_content_type = data['v'][0]['v'][0]['type']
                    sse_message_content = data['v'][0]['v'][0]['content']
            elif data.get('p') == 'response/fragments' and data.get('v'):
                sse_message_content_type = data['v'][0]['type']
                sse_message_content = data['v'][0]['content']
            elif data.get('p') == 'response/fragments/-1' and data.get('v'): sse_message_content = data['v'][0]['v']
            elif data.get('p') == 'response/fragments/-1/content' and data.get('v'): sse_message_content = data['v']
        elif not data.get('v') is None:
            if type(data['v']) == str: sse_message_content = data['v']
            elif type(data['v']) == list: sse_message_content = data['v'][0]['v']
            elif type(data['v']) == dict:
                message_data = data['v']['response']
                self.message_id = message_data['message_id']
                self.parent_message_id = message_data['parent_id']
                self.role = message_data['role']
                
                sse_message_content_type = message_data['fragments'][0]['type']
                sse_message_content = message_data['fragments'][0]['content']
        
        return sse_message_content_type, sse_message_content
    
    
    def _process_sse_message(self, sse_message_event_type: str, sse_message_content_type: str, sse_message: str, stream: bool = False) -> tuple[str, str]:
        data = json.loads(sse_message[6:])
        
        sse_message_content = ''
        if sse_message_event_type == self.event_files_type:
            sse_message_content = {
                'file_id': data['id'], 
                'name': data['file_name'], 
                'size': data['file_size']
            }
            if stream: sse_message_content = json.dumps(sse_message_content)
        elif sse_message_event_type == self.event_session_type:
            sse_message_content_type, sse_message_content = self._parse_sse_message(sse_message_content_type, sse_message)
            if stream and sse_message_content: sse_message_content = json.dumps({'content': sse_message_content})
        
        if stream: sse_message_content = f'data: {sse_message_content}\n\n' if sse_message_content else ''
        return sse_message_content_type, sse_message_content
    
    
    async def fetch(self, config: Config, chat_id: str, parent_message_id: int, prompt: str, file_ids: list[str] | None = None) -> None:
        try:
            request_data = await self._get_request_data(config, chat_id, parent_message_id, prompt, file_ids=file_ids)
            if request_data is None: return None
            
            async with AsyncSession() as session:
                response = await session.post(
                    f'{self._data.scheme}{self._data.authority}/api/v0/chat/completion', 
                    impersonate=self._data.impersonate, 
                    headers = request_data[0], 
                    json = request_data[1], 
                    stream=False
                )
            
            if response.status_code == 200:
                lines = response.text.split('\n')
                if not lines:
                    self.exception_detail = 'Empty response' 
                    return None
                
                status = self._check_sse_response_status(lines[0])
                if not status: return None
                
                i = 1
                self.think, self.content = [], []
                event_type, content_type = '', ''
                while i < len(lines) and lines[i] != 'event: close':
                    line = lines[i]
                    if not line: i += 1; continue
                    
                    if line.startswith('event: '):
                        if line == 'event: update_file':
                            event_type = self.event_files_type
                        elif line == 'event: update_session':
                            event_type = self.event_session_type
                    elif line.startswith('data: '):
                        content_type, content = self._process_sse_message(event_type, content_type, line, stream=False)
                        if event_type == self.event_files_type:
                            self.files.append(content)
                        elif event_type == self.event_session_type:
                            if not content: i += 1; continue
                            if content_type == 'RESPONSE': self.content.append(content)
                            else: self.think.append(content)
                    i += 1
                if not self.think: self.think = None
                else: self.think = ''.join(self.think)
                
                if not self.content:
                    self.exception_detail = 'Empty response'
                    return None
                else: self.content = ''.join(self.content)
                    
                if self._data.debug: logger.info(f'[Message] Output: {self.content[:30]}...')
            else:
                self.exception_detail = response.text
                if self._data.debug: logger.error(f'[Message] Response exception | Detail: {self.exception_detail}')
        except Exception as e:
            self.exception_detail = str(e)
            if self._data.debug: logger.error(f'[Message] Unknown exception | Detail: {self.exception_detail}')
            print_exc()
    
    
    async def fetch_stream(self, config: Config, chat_id: str, parent_message_id: int, prompt: str, file_ids: list[str] | None = None) -> None:
        try:
            request_data = await self._get_request_data(config, chat_id, parent_message_id, prompt, file_ids=file_ids)
            if request_data is None:
                yield 'event: error\n'
                yield f'data: {json.dumps({"error": self.exception_detail})}\n\n'
                return
            
            async with AsyncSession() as session:
                response = await session.post(
                    f'{self._data.scheme}{self._data.authority}/api/v0/chat/completion', 
                    impersonate=self._data.impersonate, 
                    headers = request_data[0], 
                    json = request_data[1], 
                    stream=True
                )
                
                lines = response.aiter_lines()
                status = await anext(lines)
                status = self._check_sse_response_status(status.decode('utf-8'))
                if not status:
                    yield 'event: error\n'
                    yield f'data: {json.dumps({"error": self.exception_detail})}\n\n'
                    return
                yield 'event: ready\n'
                
                event_type, content_type = '', ''
                async for line in lines:
                    if not line: continue
                    line = line.decode('utf-8')
                    
                    if line.startswith('event: '):
                        if line == 'event: update_file':
                            if event_type != self.event_files_type:
                                yield 'event: update_files\n'
                            event_type = self.event_files_type
                        elif line == 'event: update_session':
                            event_type = self.event_session_type
                        elif line == 'event: close':
                            break
                    elif line.startswith('data: '):
                        new_content_type, content = self._process_sse_message(event_type, content_type, line, stream=True)
                        if new_content_type != content_type:
                            if event_type == self.event_session_type:
                                yield 'event: update_session\n'
                                yield f'data: {json.dumps({"type": new_content_type})}\n\n'
                        content_type = new_content_type
                        if content:
                            yield content
        except Exception as e:
            self.exception_detail = str(e)
            yield 'event: error\n'
            yield f'data: {json.dumps({"error": self.exception_detail})}\n\n'
            if self._data.debug: logger.error(f'[Message] Unknown exception | Detail: {self.exception_detail}')
            print_exc()