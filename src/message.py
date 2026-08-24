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
        self.reply = None
        self.files = []
    
    
    async def fetch(self, config: Config, chat_id: str, parent_message_id: int, prompt: str, file_ids: list[str] | None = None) -> None:
        try:
            x_ds_pow_response = POWChallenge(self._data)
            await x_ds_pow_response.fetch('/api/v0/chat/completion')
            if not x_ds_pow_response.exception_detail is None:
                self.exception_detail = x_ds_pow_response.exception_detail
                return None
            
            headers = self._data.headers.copy()
            headers['x-ds-pow-response'] = x_ds_pow_response.result
            
            ref_file_ids = file_ids or []
            
            async with AsyncSession() as session:
                response = await session.post(
                    f'{self._data.scheme}{self._data.authority}/api/v0/chat/completion', 
                    headers = headers, 
                    impersonate=self._data.impersonate, 
                    json = {
                        'chat_session_id': chat_id, 
                        'parent_message_id': parent_message_id, 
                        'model_type': config.model, 
                        'preempt': False, 
                        'prompt': prompt, 
                        'ref_file_ids': ref_file_ids, 
                        'search_enabled': config.search_enabled if config.model == 'default' else False, 
                        'thinking_enabled': config.thinking_enabled
                    }, 
                    stream=False
                )
            
            if response.status_code == 200:
                lines = response.text.split('\n')
                if not lines:
                    self.exception_detail = 'Empty response' 
                    return None
                
                status = lines[0]
                
                if status == 'event: ready':
                    self.think = []
                    self.reply = []
                    
                    f_lines = lines
                    for i in range(len(f_lines)):
                        if f_lines[i] == 'event: update_file':
                            file_json = json.loads(f_lines[i+1][6:])
                            self.files.append({
                                'file_id': file_json['id'], 
                                'name': file_json['file_name'], 
                                'size': file_json['file_size']
                            })
                    
                    i = 0
                    while i < len(lines) and lines[i] != 'event: update_session':
                        if lines[i] == 'event: close':
                            self.exception_detail = 'Empty response. The current model may not support the uploaded file. Try removing the file or switching to a compatible model (e.g., files uploaded for "vision" model may not work with "default" or "expert" models).'
                            return None
                        i += 1
                    lines = lines[i+3:]
                    
                    if not lines or not lines[0].startswith('data: '):
                        self.exception_detail = 'Unknown response format'
                        return None
                    message_data = json.loads(lines[0][6:])['v']['response']
                    self.message_id = message_data['message_id']
                    self.parent_message_id = message_data['parent_id']
                    self.role = message_data['role']
                    
                    content_type = message_data['fragments'][0]['type']
                    content = message_data['fragments'][0]['content']
                    
                    if content:
                        if content_type == 'RESPONSE': self.reply.append(content)
                        else: self.think.append(content)
                    
                    i = 1
                    while i < len(lines):
                        line = lines[i]
                        if not line or not line.startswith('data'): i += 1; continue
                        data = json.loads(line[6:])
                        content = ''
                        
                        if not data.get('p') is None:
                            if data.get('p') == 'response' and data.get('v'):
                                if type(data['v'][0]['v']) == list and not data['v'][0]['v'][0].get('content') is None:
                                    content_type = data['v'][0]['v'][0]['type']
                                    content = data['v'][0]['v'][0]['content']
                            elif data.get('p') == 'response/fragments' and data.get('v'):
                                content_type = data['v'][0]['type']
                                content = data['v'][0]['content']
                            elif data.get('p') == 'response/fragments/-1' and data.get('v'): content = data['v'][0]['v']
                            elif data.get('p') == 'response/fragments/-1/content' and data.get('v'): content = data['v']
                        else:
                            if not data.get('v') is None:
                                if type(data['v']) == str: content = data['v']
                                elif type(data['v']) == list: content = data['v'][0]['v']
                        if content:
                            if content_type == 'RESPONSE': self.reply.append(content)
                            else: self.think.append(content)
                        i += 1
                    if not self.think: self.think = None
                    else: self.think = ''.join(self.think)
                    
                    if not self.reply:
                        self.exception_detail = 'Empty response'
                        return None
                    else: self.reply = ''.join(self.reply)
                    
                    if self._data.debug: logger.info(f'[Message] Output: {self.reply[:30]}...')
                else:
                    try:
                        status = json.loads(status)
                        self.exception_detail = status['data']['biz_msg']
                    except:
                        self.exception_detail = status
                    if self._data.debug: logger.error(f'[Message] SSE exception | Detail: {self.exception_detail}')
            else:
                self.exception_detail = response.text
                if self._data.debug: logger.error(f'[Message] Response exception | Detail: {self.exception_detail}')
        except Exception as e:
            self.exception_detail = str(e)
            if self._data.debug: logger.error(f'[Message] Unknown exception | Detail: {self.exception_detail}')
            print_exc()