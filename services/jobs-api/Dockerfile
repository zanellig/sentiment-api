# The Jobs API image (ADR-0001). Build context is the repo root: the workspace lock lives there.
FROM astral/uv:0.13.7-python3.12-trixie-slim

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1
WORKDIR /app
COPY . .
# Only this member and its dependencies, at the versions in uv.lock.
RUN uv sync --locked --package jobs-api --no-editable && rm -rf /root/.cache/uv
ENV PATH="/app/.venv/bin:$PATH"

USER nobody

EXPOSE 8000
# shortcut: replicas starting together on an unmigrated database race in Alembic, move migrations to a one-off job before running more than one replica.
CMD ["sh", "-c", "alembic -c services/jobs-api/alembic.ini upgrade head && exec uvicorn jobs_api.http:app --host 0.0.0.0 --port 8000"]
