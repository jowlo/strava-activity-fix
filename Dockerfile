FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

VOLUME /config

ENV CONFIG_PATH=/config/config.yaml
ENV TOKENS_PATH=/config/tokens.json
ENV STATE_PATH=/config/state.json

ENTRYPOINT ["python", "-m", "app.main"]
