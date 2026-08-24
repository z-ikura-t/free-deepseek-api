import os, json, struct, base64, asyncio

from loguru import logger
from traceback import print_exc
from curl_cffi.requests import AsyncSession
from wasmtime import Engine, Store, Module, Instance, Memory, Func

from .data import Data
from .utils import extract_from_response



class POWChallenge:
    def __init__(self, data: Data):
        self._data = data
        
        self.exception_detail = None
        
        self.result = None
    
    
    def _encode_string(self, store: Store, memory: Memory, malloc: Func, text: str) -> tuple[int, int]:
        bytes_data = text.encode('utf-8')
        length = len(bytes_data)
        ptr = malloc(store, length, 1)
        memory_data = memory.data_ptr(store)
        for i in range(length):
            memory_data[ptr + i] = bytes_data[i]
        return ptr, length
    
    
    async def _solve_pow_wasm(self, challenge: str, salt: str, expire_at: int, difficulty: int) -> int | None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        wasm_path = os.path.join(script_dir, 'pow_challenge.wasm')
        
        if not os.path.exists(wasm_path):
            self.exception_detail = f'WASM file not found: {wasm_path}'
            return None
        
        engine = Engine()
        store = Store(engine)
        
        with open(wasm_path, 'rb') as file: wasm_bytes = file.read()
        
        module = Module(engine, wasm_bytes)
        instance = Instance(store, module, [])
        exports = instance.exports(store)
        
        wasm_solve = exports['wasm_solve']
        malloc = exports['__wbindgen_export_0']
        memory = exports['memory']
        stack_ptr_func = exports['__wbindgen_add_to_stack_pointer']
        
        stack_ptr = stack_ptr_func(store, -16)
        prefix = f'{salt}_{expire_at}_'
        
        ch_ptr, ch_len = self._encode_string(store, memory, malloc, challenge)
        pr_ptr, pr_len = self._encode_string(store, memory, malloc, prefix)
        
        wasm_solve(store, stack_ptr, ch_ptr, ch_len, pr_ptr, pr_len, float(difficulty))
        
        memory_data = memory.data_ptr(store)
        result_bytes = bytes([memory_data[stack_ptr + 8 + i] for i in range(8)])
        result = struct.unpack('<d', result_bytes)[0]
        
        stack_ptr_func(store, 16)
        
        return int(result)
    
    
    async def _solve_pow_challenge(self, challenge: str, salt: str, expire_at: int, difficulty: int, algorithm: str, signature: str, target_path: str) -> str | None:
        answer = await self._solve_pow_wasm(challenge, salt, expire_at, difficulty)
        if answer is None: return None
        
        X_DS_POW_RESPONSE_json = json.dumps({
            'algorithm': algorithm, 
            'challenge': challenge, 
            'salt': salt, 
            'answer': answer, 
            'signature': signature, 
            'target_path': target_path
        }, separators=(',', ':'))
        X_DS_POW_RESPONSE_b64 = base64.b64encode(X_DS_POW_RESPONSE_json.encode()).decode()
        return X_DS_POW_RESPONSE_b64
    
    
    async def fetch(self, target_path: str) -> None:
        try:
            async with AsyncSession() as session:
                response = await session.post(
                    f'{self._data.scheme}{self._data.authority}/api/v0/chat/create_pow_challenge', 
                    headers = self._data.headers, 
                    impersonate=self._data.impersonate, 
                    json = {
                        'target_path': target_path
                    }
                )
            
            response = await extract_from_response('POW challenge', response, debug=self._data.debug)
            if not response[0]:
                self.exception_detail = response[1]
                return None
            else: response = response[1]
            
            pow_challenge = response['data']['biz_data']['challenge']
            if self._data.debug: logger.info('[POW challenge] Created')
            
            algorithm = pow_challenge['algorithm']
            challenge = pow_challenge['challenge']
            salt = pow_challenge['salt']
            signature = pow_challenge['signature']
            difficulty = pow_challenge['difficulty']
            expire_at = pow_challenge['expire_at']
            
            X_DS_POW_RESPONSE_b64 = await self._solve_pow_challenge(challenge, salt, expire_at, difficulty, algorithm, signature, target_path)
            if X_DS_POW_RESPONSE_b64 is None: return None
            
            if self._data.debug: logger.info(f'[POW challenge] Solved | Result: {X_DS_POW_RESPONSE_b64[:40]}...')
            self.result = X_DS_POW_RESPONSE_b64
        except Exception as e:
            self.exception_detail = str(e)
            if self._data.debug: logger.error(f'[POW challenge] Unknown exception | Detail: {self.exception_detail}')
            print_exc()