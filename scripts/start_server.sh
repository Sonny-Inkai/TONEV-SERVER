# scripts/start_server.sh
#!/bin/bash
set -e

echo "Starting TTS Server..."
exec python -m uvicorn src.main:app \
    --host ${HOST:-0.0.0.0} \
    --port ${PORT:-8000} \
    --workers 1 \
    --log-level ${LOG_LEVEL:-info} \
    --proxy-headers \
    --forwarded-allow-ips='*'