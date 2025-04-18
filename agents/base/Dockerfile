FROM python:3.11-slim
WORKDIR /app
COPY entrypoint.py /app/entrypoint.py
RUN pip install --no-cache-dir crewai==0.2.* confluent-kafka flask playwright python-dotenv \
    && playwright install --with-deps chromium
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "/app/entrypoint.py"] 