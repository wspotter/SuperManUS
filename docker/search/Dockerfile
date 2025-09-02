FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    duckduckgo-search \
    googlesearch-python \
    beautifulsoup4 \
    requests \
    selenium \
    webdriver-manager \
    aiohttp \
    fastapi \
    uvicorn

COPY src/search/ ./

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "search_service.py"]