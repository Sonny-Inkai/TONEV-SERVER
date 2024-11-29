# src/api/websocket.py
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator, Optional, Dict, Any
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, ValidationError

from ..core.config import get_settings
from ..core.errors import WebSocketError
from ..core.logger import logger
from ..tts.model import get_tts_model
from ..tts.stream import stream_manager, AudioStream
from .dependencies import ws_manager

settings = get_settings()

class WSMessageHandler:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.stream: Optional[AudioStream] = None
        self.session_id = str(uuid4())
        self.tts_model = get_tts_model()
        self._active = True
        self._message_queue = asyncio.Queue()
        self._tasks: list[asyncio.Task] = []

    async def initialize(self) -> None:
        try:
            self.stream = await stream_manager.create_stream(self.websocket)
            self._tasks.append(asyncio.create_task(self._process_messages()))
            self._tasks.append(asyncio.create_task(self._handle_keepalive()))
            logger.info(f"WebSocket handler initialized: {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket handler: {e}")
            raise WebSocketError("WebSocket initialization failed")

    async def _handle_keepalive(self) -> None:
        """Handle WebSocket keepalive."""
        while self._active:
            try:
                await asyncio.sleep(settings.WS_PING_INTERVAL)
                await self.websocket.send_json({"type": "ping"})
            except Exception as e:
                logger.error(f"Keepalive error: {e}")
                await self.cleanup()
                break

    async def _process_messages(self) -> None:
        """Process messages from the queue."""
        while self._active:
            try:
                message = await self._message_queue.get()
                await self._handle_message(message)
            except Exception as e:
                logger.error(f"Message processing error: {e}")
                continue

    async def handle_incoming_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming WebSocket message."""
        await self._message_queue.put(message)

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle individual WebSocket message."""
        try:
            message_type = message.get("type")
            
            if message_type == "synthesize":
                await self._handle_synthesis(message)
            elif message_type == "pong":
                pass  # Keepalive response
            elif message_type == "stop":
                await self._handle_stop()
            elif message_type == "configure":
                await self._handle_configure(message)
            else:
                await self._send_error("Unknown message type")

        except Exception as e:
            logger.error(f"Message handling error: {e}")
            await self._send_error(str(e))

    async def _handle_synthesis(self, message: Dict[str, Any]) -> None:
        """Handle synthesis request."""
        try:
            if not self.stream:
                raise WebSocketError("Stream not initialized")

            text = message.get("text")
            if not text:
                await self._send_error("No text provided")
                return

            voice = message.get("voice", "default")
            speed = float(message.get("speed", 1.0))

            synthesis_task = asyncio.create_task(
                self.stream.stream_audio(text, voice, speed)
            )
            self._tasks.append(synthesis_task)

            await synthesis_task

        except Exception as e:
            logger.error(f"Synthesis error: {e}")
            await self._send_error("Synthesis failed")

    async def _handle_stop(self) -> None:
        """Handle stop request."""
        try:
            if self.stream:
                await self.stream.close()
            await self._send_success("Streaming stopped")
        except Exception as e:
            logger.error(f"Stop error: {e}")
            await self._send_error("Failed to stop streaming")

    async def _handle_configure(self, message: Dict[str, Any]) -> None:
        """Handle configuration update."""
        try:
            # Update stream configuration if needed
            await self._send_success("Configuration updated")
        except Exception as e:
            logger.error(f"Configuration error: {e}")
            await self._send_error("Failed to update configuration")

    async def _send_error(self, message: str) -> None:
        """Send error message to client."""
        try:
            await self.websocket.send_json({
                "type": "error",
                "message": message
            })
        except Exception as e:
            logger.error(f"Error sending error message: {e}")

    async def _send_success(self, message: str) -> None:
        """Send success message to client."""
        try:
            await self.websocket.send_json({
                "type": "success",
                "message": message
            })
        except Exception as e:
            logger.error(f"Error sending success message: {e}")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._active = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Close stream
        if self.stream:
            await self.stream.close()
        
        # Remove from manager
        await ws_manager.disconnect(self.session_id)
        
        logger.info(f"WebSocket handler cleaned up: {self.session_id}")

async def websocket_endpoint_handler(websocket: WebSocket) -> None:
    """Main WebSocket endpoint handler."""
    handler = WSMessageHandler(websocket)
    
    try:
        await handler.initialize()
        
        while True:
            try:
                message = await websocket.receive_json()
                await handler.handle_incoming_message(message)
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {handler.session_id}")
                break
            except json.JSONDecodeError:
                await handler._send_error("Invalid JSON message")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket handler error: {e}")
    finally:
        await handler.cleanup()