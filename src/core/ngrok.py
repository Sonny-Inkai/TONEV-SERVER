from __future__ import annotations

import asyncio
from typing import Optional
from pyngrok import ngrok, conf
import requests

from .config import get_settings
from .logger import logger

settings = get_settings()

class NgrokManager:
    def __init__(self, port: int = settings.PORT, auth_token: Optional[str] = None) -> None:
        self.port = port
        self.tunnel = None
        if auth_token:
            ngrok.set_auth_token(auth_token)

    async def start(self) -> str:
        """Start ngrok tunnel."""
        try:
            # Configure ngrok
            conf.get_default().region = 'us'
            conf.get_default().console_ui = False
            
            # Start tunnel
            self.tunnel = ngrok.connect(
                addr=f"http://localhost:{self.port}",
                bind_tls=True,
                proto="http"
            )
            
            # Get public URL
            public_url = self.tunnel.public_url
            logger.info(f"Ngrok tunnel established: {public_url}")
            
            return public_url

        except Exception as e:
            logger.error(f"Failed to start ngrok tunnel: {str(e)}")
            raise

    async def stop(self) -> None:
        """Stop ngrok tunnel."""
        try:
            if self.tunnel:
                ngrok.disconnect(self.tunnel.public_url)
                self.tunnel = None
                logger.info("Ngrok tunnel closed")
        except Exception as e:
            logger.error(f"Failed to stop ngrok tunnel: {str(e)}")
            raise

    @staticmethod
    async def get_tunnels() -> list[str]:
        """Get list of active tunnels."""
        try:
            tunnels = ngrok.get_tunnels()
            return [tunnel.public_url for tunnel in tunnels]
        except Exception as e:
            logger.error(f"Failed to get ngrok tunnels: {str(e)}")
            raise

    async def check_tunnel_status(self) -> bool:
        """Check if tunnel is active."""
        if not self.tunnel:
            return False
            
        try:
            response = requests.get(f"{self.tunnel.public_url}/health")
            return response.status_code == 200
        except:
            return False