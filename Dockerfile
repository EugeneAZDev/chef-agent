FROM python:3.13-slim
WORKDIR /app
RUN pip install --no-cache-dir poetry
COPY pyproject.toml .
RUN poetry install --no-root --only main
COPY . .
EXPOSE 8000
CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
