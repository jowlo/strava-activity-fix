FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app/ ./app/
RUN uv sync --frozen --no-dev

VOLUME /config

ENV CONFIG_PATH=/config/config.yaml
ENV TOKENS_PATH=/config/tokens.json
ENV STATE_PATH=/config/state.json

ENTRYPOINT ["uv", "run", "strava-activity-hide"]
