# TONEV-SERVER
# Text-to-Speech Server

This is a FastAPI-based Text-to-Speech server that converts text to speech using the Coqui TTS engine. The server provides HTTP streaming capabilities for efficient audio delivery.

## Prerequisites

Before running the server, ensure you have the following installed:
- Python 3.8 or higher
- pip (Python package manager)

## Installation

First, create and activate a virtual environment:

```bash
python -m venv svenv
source svenv/bin/activate  # On Windows, use: svenv\Scripts\activate
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

The server configuration is managed through environment variables or a .env file. Create a .env file in the project root with the following settings:

```env
HOST=0.0.0.0
PORT=8000
SAMPLE_RATE=24000
NUM_CHANNELS=1
MODEL_NAME=tts_models/en/ljspeech/fast_pitch
DEVICE=cuda  # Use 'cpu' if no GPU is available
```

## Running the Server

Start the server using uvicorn:

```bash
uvicorn src.main:app --reload
```

The server will be available at http://localhost:8000

## API Endpoints

The server exposes the following endpoints:

- `GET /health`: Check server status
- `POST /synthesize`: Convert text to speech
- `GET /voices`: List available voices

## Testing the Server

You can test the synthesis endpoint using curl:

```bash
curl -X POST http://localhost:8000/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello world", "voice":"default", "speed":1.0}' \
  --output output.wav
```

## Project Structure

```
src/
├── api/
│   ├── routes.py        # API endpoints
│   └── dependencies.py  # FastAPI dependencies
├── core/
│   ├── config.py       # Configuration management
│   └── errors.py       # Error definitions
├── tts/
│   ├── model.py        # TTS model implementation
│   └── audio.py        # Audio processing utilities
└── main.py            # Application entry point
```

## Common Issues

If you encounter the error "Failed to initialize TTS model", ensure that:
- You have sufficient GPU memory (if using CUDA)
- The model path in your configuration is correct
- You have internet access for the initial model download

For additional support or feature requests, please open an issue in the repository.