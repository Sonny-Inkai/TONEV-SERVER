# docker/Dockerfile
FROM nvidia/cuda:11.8.0-base-ubuntu22.04 as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.4.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv"

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

# Build stage
FROM base as builder

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    curl \
    build-essential \
    python3.10 \
    python3.10-dev \
    python3.10-venv \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR $PYSETUP_PATH
COPY poetry.lock pyproject.toml ./
COPY src ./src

RUN poetry install --no-dev

# Runtime stage
FROM base as runtime

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    python3.10 \
    python3.10-venv \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder $PYSETUP_PATH $PYSETUP_PATH
COPY scripts/download_models.sh /scripts/
COPY scripts/start_server.sh /scripts/

# Make scripts executable
RUN chmod +x /scripts/download_models.sh \
    && chmod +x /scripts/start_server.sh

WORKDIR /app
COPY . .

# Download models during build
RUN /scripts/download_models.sh

EXPOSE 8000

CMD ["/scripts/start_server.sh"]