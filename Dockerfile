FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN pip install uv && uv sync --no-dev

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uv run python scripts/migrate.py && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
