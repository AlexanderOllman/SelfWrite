FROM python:3.11-slim
WORKDIR /app

# Install only essential packages first
RUN pip install --no-cache-dir \
    confluent-kafka \
    flask \
    python-dotenv \
    crewai==0.2.0

# Copy the entrypoint script
COPY entrypoint.py /app/entrypoint.py
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "/app/entrypoint.py"] 