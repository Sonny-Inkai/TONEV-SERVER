# src/tts/stream.py
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import AsyncGenerator, Optional

import numpy as np
from fastapi import WebSocket

from ..core.config import get_settings
from ..core.errors import WebSocketError
from ..core.logger import logger
from .audio import audio_processor
from .model import get_tts_model

settings = get_settings()

@dataclass
class StreamConfig:
    chunk_size: int = settings.CHUNK_SIZE
    sample_rate: int = settings.SAMPLE_RATE
    num_channels: int = settings.NUM_CHANNELS
    ping_interval: float = settings.WS_PING_INTERVAL
    ping_timeout: float = settings.WS_PING_TIMEOUT

class AudioStream:
    def __init__(self, websocket: WebSocket, config: Optional[StreamConfig] = None) -> None:
        self.websocket = websocket
        self.config = config or StreamConfig()
        self.session_id = str(uuid.uuid4())
        self._tts_model = get_tts_model()
        self._active = True
        self._ping_task: Optional[asyncio.Task] = None
        self._stream_task: Optional[asyncio.Task] = None
        self._buffer = asyncio.Queue()
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize WebSocket connection and start ping task."""
        try:
            await self.websocket.accept()
            self._ping_task = asyncio.create_task(self._keep_alive())
            logger.info(f"WebSocket connection initialized: {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket: {str(e)}")
            raise WebSocketError("Failed to initialize WebSocket connection")

    async def _keep_alive(self) -> None:
        """Send periodic pings to keep WebSocket connection alive."""
        try:
            while self._active:
                await asyncio.sleep(self.config.ping_interval)
                try:
                    pong_waiter = await self.websocket.ping()
                    await asyncio.wait_for(pong_waiter, timeout=self.config.ping_timeout)
                except asyncio.TimeoutError:
                    logger.warning(f"WebSocket ping timeout: {self.session_id}")
                    await self.close()
                    break
        except Exception as e:
            logger.error(f"Keep-alive error: {str(e)}")
            await self.close()

    async def stream_audio(
        self,
        text: str,
        voice: str = "default",
        speed: float = 1.0
    ) -> None:
        """Stream audio data through WebSocket."""
        try:
            async with self._lock:
                async for chunk in self._tts_model.generate_speech_stream(
                    text=text,
                    voice=voice,
                    speed=speed,
                    chunk_size=self.config.chunk_size
                ):
                    if not self._active:
                        break

                    await self.websocket.send_bytes(chunk)
                    
                # Send end-of-stream marker
                if self._active:
                    await self.websocket.send_json({"type": "end"})

        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            await self.close()
            raise WebSocketError("Audio streaming failed", details={"error": str(e)})

    async def handle_messages(self) -> None:
        """Handle incoming WebSocket messages."""
        try:
            while self._active:
                try:
                    message = await self.websocket.receive_json()
                    
                    if message.get("type") == "synthesize":
                        text = message.get("text", "")
                        voice = message.get("voice", "default")
                        speed = float(message.get("speed", 1.0))
                        
                        if not text:
                            await self.websocket.send_json({
                                "type": "error",
                                "message": "Text is required"
                            })
                            continue

                        await self.stream_audio(text, voice, speed)
                    
                    elif message.get("type") == "stop":
                        await self.close()
                        break

                except Exception as e:
                    logger.error(f"Message handling error: {str(e)}")
                    await self.websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })

        except Exception as e:
            logger.error(f"WebSocket message handling failed: {str(e)}")
            await self.close()

    async def close(self) -> None:
        """Close WebSocket connection and cleanup resources."""
        self._active = False
        
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass

        if self._stream_task:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass

        try:
            await self.websocket.close()
        except Exception:
            pass

        logger.info(f"WebSocket connection closed: {self.session_id}")

class StreamManager:
    def __init__(self) -> None:
        self._streams: dict[str, AudioStream] = {}
        self._lock = asyncio.Lock()

    async def create_stream(self, websocket: WebSocket) -> AudioStream:
        """Create and initialize new audio stream."""
        stream = AudioStream(websocket)
        await stream.initialize()
        
        async with self._lock:
            self._streams[stream.session_id] = stream
        
        return stream

    async def remove_stream(self, session_id: str) -> None:
        """Remove audio stream."""
        async with self._lock:
            if session_id in self._streams:
                await self._streams[session_id].close()
                del self._streams[session_id]

    def get_stream(self, session_id: str) -> Optional[AudioStream]:
        """Get audio stream by session ID."""
        return self._streams.get(session_id)

    @property
    def active_streams(self) -> int:
        """Get number of active streams."""
        return len(self._streams)

stream_manager = StreamManager()