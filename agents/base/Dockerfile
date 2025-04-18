FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    curl \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages individually to better identify issues if they occur
RUN pip install --no-cache-dir confluent-kafka==2.2.0 \
    && pip install --no-cache-dir flask \
    && pip install --no-cache-dir python-dotenv \
    && pip install --no-cache-dir crewai==0.2.0 \
    && pip install --no-cache-dir playwright \
    && playwright install --with-deps chromium

COPY entrypoint.py /app/entrypoint.py
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "/app/entrypoint.py"] 