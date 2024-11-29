# src/tts/audio.py
from __future__ import annotations

import io
import wave
import numpy as np
from typing import Optional, Tuple
import soundfile as sf
from pydub import AudioSegment
from pydub.utils import make_chunks

from ..core.config import get_settings
from ..core.errors import AudioError
from ..core.logger import logger

settings = get_settings()

class AudioProcessor:
    def __init__(
        self,
        sample_rate: int = settings.SAMPLE_RATE,
        num_channels: int = settings.NUM_CHANNELS,
        chunk_size: int = settings.CHUNK_SIZE
    ) -> None:
        self.sample_rate = sample_rate
        self.num_channels = num_channels
        self.chunk_size = chunk_size

    def array_to_wav_bytes(self, audio_array: np.ndarray) -> bytes:
        """Convert numpy array to WAV bytes."""
        try:
            bytes_io = io.BytesIO()
            with wave.open(bytes_io, 'wb') as wav:
                wav.setnchannels(self.num_channels)
                wav.setsampwidth(2)  # 16-bit
                wav.setframerate(self.sample_rate)
                wav.writeframes(audio_array.tobytes())
            return bytes_io.getvalue()
        except Exception as e:
            logger.error(f"Failed to convert array to WAV: {str(e)}")
            raise AudioError("Failed to convert array to WAV", details={"error": str(e)})

    def wav_bytes_to_array(self, wav_bytes: bytes) -> Tuple[np.ndarray, int]:
        """Convert WAV bytes to numpy array."""
        try:
            with io.BytesIO(wav_bytes) as bytes_io:
                with wave.open(bytes_io, 'rb') as wav:
                    frames = wav.readframes(wav.getnframes())
                    array = np.frombuffer(frames, dtype=np.int16)
                    sample_rate = wav.getframerate()
            return array, sample_rate
        except Exception as e:
            logger.error(f"Failed to convert WAV to array: {str(e)}")
            raise AudioError("Failed to convert WAV to array", details={"error": str(e)})

    def normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """Normalize audio to prevent clipping."""
        try:
            max_val = np.abs(audio).max()
            if max_val > 0:
                return (audio * 32767 / max_val).astype(np.int16)
            return audio.astype(np.int16)
        except Exception as e:
            logger.error(f"Audio normalization failed: {str(e)}")
            raise AudioError("Audio normalization failed", details={"error": str(e)})

    def resample_audio(self, audio: np.ndarray, original_rate: int) -> np.ndarray:
        """Resample audio to target sample rate."""
        try:
            if original_rate == self.sample_rate:
                return audio

            bytes_io = io.BytesIO()
            sf.write(bytes_io, audio, original_rate, format='WAV')
            bytes_io.seek(0)
            
            audio_segment = AudioSegment.from_wav(bytes_io)
            resampled = audio_segment.set_frame_rate(self.sample_rate)
            
            output_io = io.BytesIO()
            resampled.export(output_io, format='wav')
            output_io.seek(0)
            
            resampled_audio, _ = sf.read(output_io)
            return (resampled_audio * 32767).astype(np.int16)
            
        except Exception as e:
            logger.error(f"Audio resampling failed: {str(e)}")
            raise AudioError("Audio resampling failed", details={"error": str(e)})

    def adjust_speed(self, audio: np.ndarray, speed: float) -> np.ndarray:
        """Adjust audio playback speed."""
        try:
            if speed == 1.0:
                return audio

            bytes_io = io.BytesIO()
            sf.write(bytes_io, audio, self.sample_rate, format='WAV')
            bytes_io.seek(0)
            
            audio_segment = AudioSegment.from_wav(bytes_io)
            adjusted = audio_segment._spawn(audio_segment.raw_data, overrides={
                "frame_rate": int(self.sample_rate * speed)
            })
            adjusted = adjusted.set_frame_rate(self.sample_rate)
            
            output_io = io.BytesIO()
            adjusted.export(output_io, format='wav')
            output_io.seek(0)
            
            adjusted_audio, _ = sf.read(output_io)
            return (adjusted_audio * 32767).astype(np.int16)
            
        except Exception as e:
            logger.error(f"Speed adjustment failed: {str(e)}")
            raise AudioError("Speed adjustment failed", details={"error": str(e)})

    def chunk_audio(self, audio: np.ndarray) -> list[bytes]:
        """Split audio into chunks."""
        try:
            bytes_io = io.BytesIO()
            sf.write(bytes_io, audio, self.sample_rate, format='WAV')
            bytes_io.seek(0)
            
            audio_segment = AudioSegment.from_wav(bytes_io)
            chunks = make_chunks(audio_segment, self.chunk_size)
            
            chunked_data = []
            for chunk in chunks:
                chunk_io = io.BytesIO()
                chunk.export(chunk_io, format='wav')
                chunked_data.append(chunk_io.getvalue())
                
            return chunked_data
            
        except Exception as e:
            logger.error(f"Audio chunking failed: {str(e)}")
            raise AudioError("Audio chunking failed", details={"error": str(e)})

    def concat_audio(self, audio_chunks: list[np.ndarray]) -> np.ndarray:
        """Concatenate multiple audio chunks."""
        try:
            return np.concatenate(audio_chunks)
        except Exception as e:
            logger.error(f"Audio concatenation failed: {str(e)}")
            raise AudioError("Audio concatenation failed", details={"error": str(e)})

    def pad_audio(self, audio: np.ndarray, target_length: int) -> np.ndarray:
        """Pad audio to target length."""
        try:
            if len(audio) >= target_length:
                return audio
            padding = np.zeros(target_length - len(audio), dtype=np.int16)
            return np.concatenate([audio, padding])
        except Exception as e:
            logger.error(f"Audio padding failed: {str(e)}")
            raise AudioError("Audio padding failed", details={"error": str(e)})

audio_processor = AudioProcessor()