from __future__ import annotations

import asyncio
from typing import AsyncGenerator, List
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import numpy as np

from ..core.config import get_settings
from ..core.errors import TTSError
from ..core.logger import logger
from ..tts.model import get_tts_model
from ..tts.audio import audio_processor
from .dependencies import get_tts, handle_tts_error

settings = get_settings()
router = APIRouter()

class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=settings.MAX_AUDIO_LENGTH)
    voice: str = Field(default="default")
    speed: float = Field(default=1.0, ge=0.5, le=2.0)

async def generate_audio_chunks(
    text: str,
    voice: str,
    speed: float,
    tts = Depends(get_tts),
    chunk_size: int = settings.CHUNK_SIZE
) -> AsyncGenerator[bytes, None]:
    """Stream audio chunks as they are generated."""
    try:
        # Generate full audio from TTS model
        audio_array = await tts.generate_speech(
            text=text,
            voice=voice,
            speed=speed
        )

        # Convert to WAV bytes
        wav_bytes = audio_processor.array_to_wav_bytes(np.array(audio_array))

        # Stream in chunks
        for i in range(0, len(wav_bytes), chunk_size):
            chunk = wav_bytes[i:i + chunk_size]
            yield chunk
            #await asyncio.sleep(0.01)  # Prevent blocking

    except Exception as e:
        logger.error(f"Audio streaming failed: {str(e)}")
        raise TTSError("Audio streaming failed", details={"error": str(e)})

@router.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.VERSION}

@router.get("/voices")
async def list_voices():
    try:
        return ["default", "male", "female"]
    except Exception as e:
        logger.error(f"Error listing voices: {str(e)}")
        raise TTSError("Failed to list voices")

@router.post("/synthesize")
async def synthesize_text(request: TTSRequest, tts = Depends(get_tts)):
    try:
        # Tạo generator để stream audio chunks
        audio_stream = generate_audio_chunks(
            text=request.text,
            voice=request.voice,
            speed=request.speed,
            tts=tts
        )
        
        # Trả về StreamingResponse
        return StreamingResponse(
            audio_stream,
            media_type="audio/wav",
            headers={
                "Cache-Control": "no-cache",
                "Content-Disposition": "attachment; filename=speech.wav"
            }
        )

    except TTSError as e:
        return await handle_tts_error(e)
    except Exception as e:
        logger.error(f"Synthesis error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Speech synthesis failed"
        )

@router.on_event("startup")
async def startup_event():
    try:
        tts = get_tts_model()
        await tts.initialize()
        logger.info("TTS model initialized successfully")
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise RuntimeError("Failed to initialize TTS model")