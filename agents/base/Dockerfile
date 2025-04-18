FROM python:3.11-slim
WORKDIR /app

# Install system dependencies for confluent-kafka (librdkafka)
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libsasl2-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install each package separately to better identify any issues
RUN set -x && pip install --no-cache-dir flask
RUN set -x && pip install --no-cache-dir python-dotenv
RUN set -x && pip install --no-cache-dir confluent-kafka || (echo "Error installing confluent-kafka" && exit 1)
RUN set -x && pip install --no-cache-dir crewai==0.2.0 || (echo "Error installing crewai" && exit 1)

# Copy the entrypoint script
COPY entrypoint.py /app/entrypoint.py
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "/app/entrypoint.py"] 