# scripts/download_models.sh
#!/bin/bash
set -e

MODEL_DIR="/app/models"
mkdir -p $MODEL_DIR

echo "Downloading TTS models..."
python3 -c "
from TTS.utils.manage import ModelManager
ModelManager().download_model('tts_models/en/vctk/vits')
"

echo "Model download complete!"