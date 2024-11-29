from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .api.routes import router as api_router
from .api.dependencies import get_tts, ws_manager
from .core.config import get_settings
from .core.errors import TTSError, WebSocketError
from .core.logger import logger
from .core.ngrok import NgrokManager
from .tts.model import get_tts_model, init_tts_model

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    try:
        # Initialize TTS model
        await init_tts_model()
        logger.info("TTS model initialized successfully")

        # Initialize ngrok if enabled
        if settings.ENABLE_NGROK:
            try:
                ngrok_manager = NgrokManager(
                    port=settings.PORT,
                    auth_token=settings.NGROK_AUTH_TOKEN
                )
                
                public_url = await ngrok_manager.start()
                app.state.ngrok_manager = ngrok_manager
                
                logger.info("Ngrok tunnel established successfully")
                logger.info(f"Public URL: {public_url}")
                
                tunnels = await ngrok_manager.get_tunnels()
                logger.info(f"Active tunnels: {tunnels}")
                
            except Exception as e:
                logger.error(f"Failed to start ngrok tunnel: {str(e)}", exc_info=True)
                raise

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        sys.exit(1)

    yield

    # Shutdown
    try:
        logger.info("Shutting down TTS service...")
        
        # Close ngrok tunnel if it exists
        if hasattr(app.state, "ngrok_manager"):
            await app.state.ngrok_manager.stop()
            logger.info("Ngrok tunnel closed successfully")

        # Close active streams
        active_streams = list(ws_manager._active_connections.keys())
        for session_id in active_streams:
            await ws_manager.disconnect(session_id)
            
        logger.info("TTS service shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )

    # CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # Register routes
    application.include_router(api_router, prefix="/api")

    @application.get("/api/status")
    async def get_status():
        """Get server status including ngrok information."""
        status = {
            "server": "running",
            "ngrok": {
                "enabled": settings.ENABLE_NGROK,
                "tunnels": []
            }
        }
        
        if hasattr(application.state, "ngrok_manager"):
            tunnels = await application.state.ngrok_manager.get_tunnels()
            status["ngrok"]["tunnels"] = tunnels
        
        return status

    @application.exception_handler(TTSError)
    async def tts_error_handler(request: Request, exc: TTSError):
        """Handle TTS-specific errors."""
        logger.error(f"TTS error: {exc.message}", extra={
            "path": request.url.path,
            "details": exc.details
        })
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        )

    @application.exception_handler(WebSocketError)
    async def websocket_error_handler(request: Request, exc: WebSocketError):
        """Handle WebSocket-specific errors."""
        logger.error(f"WebSocket error: {exc.message}", extra={
            "path": request.url.path,
            "details": exc.details
        })
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        logger.warning(f"Validation error", extra={
            "path": request.url.path,
            "errors": exc.errors()
        })
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "code": "VALIDATION_ERROR",
                "message": "Validation error",
                "details": {"errors": exc.errors()}
            }
        )

    @application.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        """Handle all unhandled exceptions."""
        logger.error(f"Unhandled error: {str(exc)}", extra={
            "path": request.url.path
        }, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "INTERNAL_ERROR",
                "message": "Internal server error"
            }
        )

    return application

app = create_application()

if __name__ == "__main__":
    import uvicorn
    
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": settings.LOG_FORMAT
            }
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr"
            }
        },
        "loggers": {
            "": {
                "handlers": ["default"],
                "level": settings.LOG_LEVEL
            }
        }
    }

    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_config=log_config,
        log_level=settings.LOG_LEVEL.lower(),
        workers=1
    )