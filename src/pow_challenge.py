from loguru import logger
import os, json, struct, base64

from curl_cffi.requests import AsyncSession
from wasmtime import Engine, Store, Module, Instance, Memory, Func

from . import settings
from .utils import extract_from_response
from .exceptions import APIError, UnknownError



class POWChallenge:
    @classmethod
    def _encode_string(cls, store: Store, memory: Memory, malloc: Func, text: str) -> tuple[int, int]:
        bytes_data = text.encode('utf-8')
        length = len(bytes_data)
        ptr = malloc(store, length, 1)
        memory_data = memory.data_ptr(store)
        for i in range(length):
            memory_data[ptr + i] = bytes_data[i]
        return ptr, length
    
    
    @classmethod
    def _solve_pow_wasm(cls, challenge: str, salt: str, expire_at: int, difficulty: int) -> int:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        wasm_path = os.path.join(script_dir, 'pow_challenge.wasm')
        
        if not os.path.exists(wasm_path): raise FileNotFoundError(f'WASM file not found: {wasm_path}')
        
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
        
        ch_ptr, ch_len = cls._encode_string(store, memory, malloc, challenge)
        pr_ptr, pr_len = cls._encode_string(store, memory, malloc, prefix)
        
        wasm_solve(store, stack_ptr, ch_ptr, ch_len, pr_ptr, pr_len, float(difficulty))
        
        memory_data = memory.data_ptr(store)
        result_bytes = bytes([memory_data[stack_ptr + 8 + i] for i in range(8)])
        result = struct.unpack('<d', result_bytes)[0]
        
        stack_ptr_func(store, 16)
        
        return int(result)
    
    
    @classmethod
    async def _solve_pow_challenge(cls, challenge: str, salt: str, expire_at: int, difficulty: int, algorithm: str, signature: str, target_path: str) -> str:
        answer = cls._solve_pow_wasm(challenge, salt, expire_at, difficulty)
        
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
    
    
    @classmethod
    async def solve(cls, target_path: str) -> dict:
        try:
            async with AsyncSession() as session:
                response = await session.post(
                    f'{settings.DEEPSEEK_URL}/chat/create_pow_challenge', 
                    headers=settings.HEADERS, 
                    impersonate=settings.IMPERSONATE, 
                    json = {
                        'target_path': target_path
                    }
                )
            
            response = extract_from_response('POW challenge', response)
            
            pow_challenge = response['data']['biz_data']['challenge']
            logger.info(f'[POW challenge] Created | Target path: {target_path}')
            
            algorithm = pow_challenge['algorithm']
            challenge = pow_challenge['challenge']
            salt = pow_challenge['salt']
            signature = pow_challenge['signature']
            difficulty = pow_challenge['difficulty']
            expire_at = pow_challenge['expire_at']
            
            X_DS_POW_RESPONSE_b64 = await cls._solve_pow_challenge(challenge, salt, expire_at, difficulty, algorithm, signature, target_path)
            
            logger.info(f'[POW challenge] Solved | Result: {X_DS_POW_RESPONSE_b64[:40]}...')
            return {
                'result': X_DS_POW_RESPONSE_b64
            }
        except (APIError, FileNotFoundError): raise
        except Exception as e:
            detail = str(e)
            logger.exception(f'[POW Challenge] Unknown exception | Detail: {detail}')
            raise UnknownError(detail) from e