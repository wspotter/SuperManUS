FROM rocm/pytorch:rocm5.7_ubuntu22.04_py3.10_pytorch_2.0.1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    diffusers \
    transformers \
    accelerate \
    opencv-python \
    pillow \
    torchvision \
    omegaconf \
    einops

COPY src/image/ ./

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ROCM_PATH=/opt/rocm
ENV HF_HOME=/app/models

CMD ["python", "image_service.py"]