class APIError(Exception):
    '''Base exception for all API-related errors.'''
    ...

class ValidationError(APIError):
    '''Raised when input validation fails (wrong date range, incorrect start/end indexes).'''
    ...

class DeepSeekError(APIError):
    '''Raised when DeepSeek returns a logical error (e.g., biz_code != 0).'''
    ...

class DeepSeekResponseError(APIError):
    '''Raised when DeepSeek response is invalid (e.g., non-200 status, malformed JSON).'''
    ...

class DeepSeekSSEError(APIError):
    '''Raised when SSE stream from DeepSeek is malformed or missing expected events.'''
    ...

class UnknownError(Exception):
    '''Raised for unexpected, unhandled exceptions.'''
    ...