FROM node:22-bookworm-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1 NEXT_PUBLIC_DEPLOYED=true
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app
COPY --from=frontend-build /usr/local/bin/node /usr/local/bin/node
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 ca-certificates && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache
COPY backend/ backend/
COPY benchmarks/ benchmarks/
COPY scripts/ scripts/
COPY experiment_lab/ experiment_lab/
COPY data/pricing.json data/pricing.json
COPY --from=frontend-build /app/frontend frontend/
ENV PYTHONUTF8=1 PYTHONUNBUFFERED=1 NEXT_TELEMETRY_DISABLED=1
EXPOSE 3000
CMD [".venv/bin/python", "scripts/serve.py"]
