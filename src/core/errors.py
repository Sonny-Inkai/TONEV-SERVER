from enum import Enum
from typing import Any, Optional

class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MODEL_ERROR = "MODEL_ERROR"
    AUDIO_ERROR = "AUDIO_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    WEBSOCKET_ERROR = "WEBSOCKET_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"

class TTSError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[dict[str, Any]] = None,
        status_code: int = 500
    ) -> None:
        self.code = code
        self.message = message
        self.details = details
        self.status_code = status_code
        super().__init__(message)

class ValidationError(TTSError):
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            details=details,
            status_code=400
        )

class ModelError(TTSError):
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(
            code=ErrorCode.MODEL_ERROR,
            message=message,  
            details=details,
            status_code=500
        )

class AudioError(TTSError):
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(
            code=ErrorCode.AUDIO_ERROR,
            message=message,
            details=details,
            status_code=500
        )

class WebSocketError(TTSError):
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(
            code=ErrorCode.WEBSOCKET_ERROR,
            message=message,
            details=details,
            status_code=400
        )