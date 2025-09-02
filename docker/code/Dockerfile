FROM rocm/pytorch:rocm5.7_ubuntu22.04_py3.10_pytorch_2.0.1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    curl \
    vim \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    transformers \
    accelerate \
    bitsandbytes \
    sentencepiece \
    protobuf \
    einops \
    langchain \
    tree-sitter \
    tree-sitter-python \
    tree-sitter-javascript

COPY src/code/ ./

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ROCM_PATH=/opt/rocm
ENV HF_HOME=/app/models

CMD ["python", "code_service.py"]