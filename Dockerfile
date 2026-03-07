FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
COPY README.md .

RUN pip install --no-cache-dir .

EXPOSE 7000

CMD ["uvicorn", "claude_scheduler.web.app:app", "--host", "0.0.0.0", "--port", "7000"]
