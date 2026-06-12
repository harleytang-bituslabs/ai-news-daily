# 日報產生器：python:3.11-slim + supercronic（容器友好的 cron，日誌走 stdout）
FROM python:3.11-slim

ENV TZ=America/Los_Angeles \
    PYTHONUNBUFFERED=1

ARG SUPERCRONIC_VERSION=v0.2.33
ARG TARGETARCH=amd64
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates tzdata \
    && curl -fsSL -o /usr/local/bin/supercronic \
       "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${TARGETARCH}" \
    && chmod +x /usr/local/bin/supercronic \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

COPY docker/crontab docker/entrypoint.sh ./docker/
RUN chmod +x docker/entrypoint.sh

ENTRYPOINT ["/app/docker/entrypoint.sh"]
