FROM python:3.13-slim

# uv instala as dependências exatamente como no uv.lock (build reprodutível)
COPY --from=ghcr.io/astral-sh/uv:0.12.22 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

# Dependências primeiro, para aproveitar o cache de camadas
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --all-extras --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY .streamlit ./.streamlit
COPY src ./src
RUN uv sync --frozen --no-dev --all-extras

ENV PATH="/app/.venv/bin:$PATH"

RUN useradd --create-home app
USER app

EXPOSE 8000
CMD ["uvicorn", "pecuaria_dados.api:app", "--host", "0.0.0.0", "--port", "8000"]
