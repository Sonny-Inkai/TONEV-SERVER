# src/tts/model.py
from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional, AsyncGenerator, Union

import numpy as np
import torch
from TTS.api import TTS

from ..core.config import get_settings
from ..core.errors import ModelError
from ..core.logger import logger

settings = get_settings()

class TTSModel:
    def __init__(self) -> None:
        self._model: Optional[TTS] = None
        self._lock = asyncio.Lock()
        self._initialized = False
        self._device = settings.DEVICE
        self._model_path = Path(settings.MODEL_PATH)
        self._sample_rate = settings.SAMPLE_RATE
        self._stream_chunk_size = settings.CHUNK_SIZE
        self._voice = settings.DEFAULT_VOICE
        self._language = settings.DEFAULT_LANGUAGE
        self._model_name = settings.MODEL_NAME

    async def initialize(self) -> None:
        if self._initialized:
            return

        try:
            async with self._lock:
                if self._initialized:
                    return

                logger.info("Initializing TTS model...")
                
                self._model = TTS(
                    model_name  =self._model_name,
                    progress_bar=False
                ).to(self._device)

                logger.info("TTS model initialized successfully")
                self._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize TTS model: {str(e)}")
            raise ModelError("Failed to initialize TTS model", details={"error": str(e)})

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise ModelError("TTS model not initialized")

    async def generate_speech(
        self,
        text: str,
        voice: str = "default",
        speed: float = 1.0,
        language: str = "en"
    ) -> np.ndarray:
        """Generate speech for entire text at once."""
        self._ensure_initialized()
        assert self._model is not None

        try:
            async with self._lock:
                if voice == "default":
                    wav = await asyncio.to_thread(
                        self._model.tts,
                        text=text,
                        #language=language,
                        speed=speed
                    )
                else:
                    wav = await asyncio.to_thread(
                        self._model.tts,
                        text=text,
                        speaker_wav=voice,
                        language=language,
                        speed=speed
                    )
                return wav

        except Exception as e:
            logger.error(f"Speech generation failed: {str(e)}")
            raise ModelError("Speech generation failed", details={"error": str(e)})

    async def generate_speech_stream(
        self,
        text: str,
        voice: str = "default",
        speed: float = 1.0,
        language: str = "en",
        chunk_size: Optional[int] = None
    ) -> AsyncGenerator[bytes, None]:
        """Generate speech in streaming mode with chunked output."""
        self._ensure_initialized()
        assert self._model is not None

        chunk_size = chunk_size or self._stream_chunk_size

        try:
            wav = await self.generate_speech(
                text=text,
                voice=voice,
                speed=speed,
                language=language
            )
            
            wav = (wav * 32767).astype(np.int16)

            for i in range(0, len(wav), chunk_size):
                chunk = wav[i:i + chunk_size]
                if len(chunk) < chunk_size:
                    chunk = np.pad(
                        chunk,
                        (0, chunk_size - len(chunk)),
                        mode='constant',
                        constant_values=0
                    )
                yield chunk.tobytes()

        except Exception as e:
            logger.error(f"Speech streaming failed: {str(e)}")
            raise ModelError("Speech streaming failed", details={"error": str(e)})

    async def voice_conversion(
        self,
        source_wav: Union[str, np.ndarray],
        target_wav: str
    ) -> np.ndarray:
        """Convert voice from source to target."""
        self._ensure_initialized()
        assert self._model is not None

        try:
            async with self._lock:
                wav = await asyncio.to_thread(
                    self._model.voice_conversion,
                    source_wav=source_wav,
                    target_wav=target_wav
                )
                return wav

        except Exception as e:
            logger.error(f"Voice conversion failed: {str(e)}")
            raise ModelError("Voice conversion failed", details={"error": str(e)})

@lru_cache()
def get_tts_model() -> TTSModel:
    """Get singleton instance of TTSModel."""
    return TTSModel()

async def init_tts_model() -> None:
    """Initialize the TTS model asynchronously."""
    model = get_tts_model()
    await model.initialize()