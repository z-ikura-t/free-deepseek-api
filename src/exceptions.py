class APIError(Exception):
    '''Base exception for all API-related errors.'''
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

class FileError(APIError):
    '''Base exception for file-related errors.'''
    ...

class FileTooLargeError(FileError):
    '''Raised when uploaded file exceeds the maximum allowed size.'''
    ...

class DeepSeekFileContentEmpty(FileError):
    '''Raised when DeepSeek cannot extract any text content from the uploaded file.'''
    ...

class DeepSeekFileUploadError(FileError):
    '''Raised when file upload to DeepSeek fails (timeout or server error).'''
    ...

class UnknownError(Exception):
    '''Raised for unexpected, unhandled exceptions.'''
    ...