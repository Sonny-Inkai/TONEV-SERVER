# scripts/start_with_ngrok.sh
#!/bin/bash

export ENABLE_NGROK=True

python -m uvicorn src.main:app \
    --host ${HOST:-0.0.0.0} \
    --port ${PORT:-8000} \
    --workers 1 \
    --log-level ${LOG_LEVEL:-info}