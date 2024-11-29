from __future__ import annotations

import io
import wave
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass

from ..core.config import get_settings
from ..core.errors import AudioError
from ..core.logger import logger

settings = get_settings()

@dataclass
class AudioConfig:
    sample_rate: int = settings.SAMPLE_RATE
    num_channels: int = settings.NUM_CHANNELS
    bits_per_sample: int = 16

class AudioProcessor:
    def __init__(
        self,
        config: Optional[AudioConfig] = None
    ) -> None:
        self.config = config or AudioConfig()

    def array_to_wav_bytes(self, audio_array: np.ndarray) -> bytes:
        """Convert numpy array from TTS model to WAV bytes."""
        try:
            # Ensure float32 array
            if audio_array.dtype != np.float32:
                audio_array = audio_array.astype(np.float32)

            # Normalize to [-1, 1] range
            if np.abs(audio_array).max() > 1.0:
                audio_array = audio_array / np.abs(audio_array).max()

            # Convert to 16-bit PCM
            wav_data = (audio_array * 32767).astype(np.int16)

            # Generate WAV file in memory
            bytes_io = io.BytesIO()
            with wave.open(bytes_io, 'wb') as wav_file:
                wav_file.setnchannels(self.config.num_channels)
                wav_file.setsampwidth(self.config.bits_per_sample // 8)
                wav_file.setframerate(self.config.sample_rate)
                wav_file.writeframes(wav_data.tobytes())
            
            return bytes_io.getvalue()

        except Exception as e:
            logger.error(f"Failed to convert array to WAV: {str(e)}")
            raise AudioError("Failed to convert array to WAV", details={"error": str(e)})

    def wav_bytes_to_array(self, wav_bytes: bytes) -> Tuple[np.ndarray, int]:
        """Convert WAV bytes back to numpy array."""
        try:
            bytes_io = io.BytesIO(wav_bytes)
            with wave.open(bytes_io, 'rb') as wav_file:
                # Get WAV file properties
                sample_rate = wav_file.getframerate()
                num_frames = wav_file.getnframes()
                
                # Read frames and convert to numpy array
                wav_data = wav_file.readframes(num_frames)
                audio_array = np.frombuffer(wav_data, dtype=np.int16)
                
                # Convert to float32 and normalize
                audio_array = audio_array.astype(np.float32) / 32767.0

                return audio_array, sample_rate

        except Exception as e:
            logger.error(f"Failed to convert WAV to array: {str(e)}")
            raise AudioError("Failed to convert WAV to array", details={"error": str(e)})

    def normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """Normalize audio to [-1, 1] range."""
        try:
            max_val = np.abs(audio).max()
            if max_val > 0:
                return audio / max_val
            return audio
            
        except Exception as e:
            logger.error(f"Audio normalization failed: {str(e)}")
            raise AudioError("Audio normalization failed", details={"error": str(e)})

audio_processor = AudioProcessor()