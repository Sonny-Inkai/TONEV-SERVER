import logging
import sys
from typing import Any

from .config import get_settings

settings = get_settings()

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(settings.LOG_LEVEL)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.LOG_LEVEL)
    formatter = logging.Formatter(settings.LOG_FORMAT)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# Get root logger
logger = setup_logger("tts_server")