# Untested on this machine (no Docker here): build with `docker build -t evopt-maps .`
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
WORKDIR /app
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY evopt ./evopt
COPY web ./web
COPY data/demo.graphml data/demo-stations.json ./data/
EXPOSE 8000
# the planner downloads roads and chargers on demand: keep them between runs with -v evopt-cache:/app/cache
CMD ["uv", "run", "--no-dev", "uvicorn", "evopt.api:app", "--host", "0.0.0.0", "--port", "8000"]
