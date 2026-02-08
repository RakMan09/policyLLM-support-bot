FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY services /app/services
COPY tests /app/tests
COPY infra /app/infra

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

EXPOSE 8001

CMD ["uvicorn", "services.tool_server.app.main:app", "--host", "0.0.0.0", "--port", "8001"]
