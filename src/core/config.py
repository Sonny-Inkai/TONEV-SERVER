# src/core/config.py
from functools import lru_cache
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
import torch 
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    # Project Information
    PROJECT_NAME: str = "TTS Server"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    ALLOWED_ORIGINS: List[str] = ["*"]

    # TTS Model Settings
    MODEL_NAME: str = "tts_models/en/ljspeech/fast_pitch" #"tts_models/multilingual/multi-dataset/xtts_v2"
    DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"
    MODEL_PATH: str = "models/"
    DEFAULT_VOICE: str = "default"
    DEFAULT_LANGUAGE: str = "en"
    
    # Audio Settings
    SAMPLE_RATE: int = 24000
    NUM_CHANNELS: int = 1
    CHUNK_SIZE: int = 4096
    MAX_AUDIO_LENGTH: int = 2000
    STREAM_BUFFER_SIZE: int = 8192
    
    # Voice Settings
    ENABLE_VOICE_CLONING: bool = False
    ENABLE_VOICE_CONVERSION: bool = True
    MAX_VOICE_DURATION: int = 30  # seconds
    
    # WebSocket Settings
    WS_PING_INTERVAL: float = 20.0
    WS_PING_TIMEOUT: float = 20.0
    MAX_CONNECTIONS: int = 100
    STREAM_CHUNK_TIMEOUT: float = 0.1
    
    # Ngrok Settings
    ENABLE_NGROK: bool = False
    NGROK_AUTH_TOKEN: Optional[str] = os.getenv("NGROK_AUTH_TOKEN")
    NGROK_REGION: str = "us"
    NGROK_TUNNEL_TIMEOUT: int = 100
    
    # Cache Settings
    CACHE_TTL: int = 3600
    MAX_CACHE_SIZE: int = 1000
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Security
    ENABLE_SSL: bool = False
    SSL_CERT_PATH: Optional[str] = None
    SSL_KEY_PATH: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

@lru_cache()
def get_settings() -> Settings:
    return Settings()