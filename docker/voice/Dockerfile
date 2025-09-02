FROM rocm/pytorch:rocm5.7_ubuntu22.04_py3.10_pytorch_2.0.1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    portaudio19-dev \
    python3-pyaudio \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    whisper \
    openai-whisper \
    TTS \
    soundfile \
    pyaudio \
    numpy \
    scipy

COPY src/voice/ ./

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ROCM_PATH=/opt/rocm

CMD ["python", "voice_service.py"]