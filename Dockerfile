# syntax=docker/dockerfile:1.7

FROM node:22-bookworm-slim AS builder

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    build-essential \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY pyproject.toml README.md ./
COPY src/novel_drama_engine ./src/novel_drama_engine
RUN python3 -m venv /opt/venv \
  && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
  && /opt/venv/bin/pip install --no-cache-dir .

COPY . .
RUN npm run build \
  && npm prune --omit=dev

FROM node:22-bookworm-slim AS runtime

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gosu \
    python3 \
    sqlite3 \
    tini \
    util-linux \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV NODE_ENV=production \
  PORT=8080 \
  PATH="/opt/venv/bin:$PATH" \
  NOVEL_DRAMA_PYTHON=/opt/venv/bin/python3

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/package.json /app/package-lock.json ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/src ./src
COPY --from=builder /app/drizzle ./drizzle
COPY --from=builder /app/drizzle.config.ts /app/next.config.ts /app/tsconfig.json ./
COPY --from=builder /app/scripts ./scripts

RUN chmod +x \
  scripts/start-zeabur.sh \
  scripts/backup-ops-data.sh \
  scripts/ops-online-readiness.sh

EXPOSE 8080

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["scripts/start-zeabur.sh"]
