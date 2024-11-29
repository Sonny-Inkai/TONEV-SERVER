# src/api/dependencies.py
from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Optional

from fastapi import WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse

from ..core.config import get_settings
from ..core.errors import TTSError, WebSocketError
from ..core.logger import logger
from ..tts.model import get_tts_model, init_tts_model
from ..tts.stream import stream_manager

settings = get_settings()

async def get_tts() -> AsyncGenerator:
    """Initialize and get TTS model for endpoints."""
    model = get_tts_model()
    if not model._initialized:
        await init_tts_model()
    try:
        yield model
    except Exception as e:
        logger.error(f"TTS model error: {str(e)}")
        raise TTSError(f"TTS model error: {str(e)}")

async def validate_connection_limit() -> bool:
    """Check if connection limit is reached."""
    if stream_manager.active_streams >= settings.MAX_CONNECTIONS:
        raise WebSocketError(
            "Maximum connection limit reached",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    return True

class WebSocketManager:
    def __init__(self) -> None:
        self._active_connections: dict[str, WebSocket] = {}
        self._connection_lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> str:
        """Handle new WebSocket connection."""
        try:
            await validate_connection_limit()
            stream = await stream_manager.create_stream(websocket)
            
            async with self._connection_lock:
                self._active_connections[stream.session_id] = websocket
            
            return stream.session_id

        except Exception as e:
            logger.error(f"WebSocket connection failed: {str(e)}")
            raise WebSocketError("Failed to establish WebSocket connection")

    async def disconnect(self, session_id: str) -> None:
        """Handle WebSocket disconnection."""
        try:
            if session_id in self._active_connections:
                async with self._connection_lock:
                    await stream_manager.remove_stream(session_id)
                    del self._active_connections[session_id]

        except Exception as e:
            logger.error(f"WebSocket disconnect error: {str(e)}")

    async def get_connection(self, session_id: str) -> Optional[WebSocket]:
        """Get WebSocket connection by session ID."""
        return self._active_connections.get(session_id)

    @property
    def active_connections(self) -> int:
        """Get number of active connections."""
        return len(self._active_connections)

    async def broadcast(self, message: str) -> None:
        """Broadcast message to all connected clients."""
        disconnected = []
        for session_id, connection in self._active_connections.items():
            try:
                await connection.send_text(message)
            except WebSocketDisconnect:
                disconnected.append(session_id)
            except Exception as e:
                logger.error(f"Broadcast error for {session_id}: {str(e)}")
                disconnected.append(session_id)

        for session_id in disconnected:
            await self.disconnect(session_id)

ws_manager = WebSocketManager()

async def handle_tts_error(error: TTSError) -> JSONResponse:
    """Handle TTS errors and return appropriate response."""
    logger.error(f"TTS error: {error.message}", extra={"details": error.details})
    return JSONResponse(
        status_code=error.status_code,
        content={
            "code": error.code,
            "message": error.message,
            "details": error.details
        }
    )

async def handle_websocket_error(error: WebSocketError) -> None:
    """Handle WebSocket errors."""
    logger.error(f"WebSocket error: {error.message}", extra={"details": error.details})
    try:
        if error.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            websocket = error.details.get("websocket")
            if websocket:
                await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER)
    except Exception as e:
        logger.error(f"Error handling WebSocket error: {str(e)}")