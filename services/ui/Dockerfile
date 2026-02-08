FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY services /app/services
COPY eval /app/eval

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e . && \
    pip install --no-cache-dir streamlit pandas

EXPOSE 8501

CMD ["streamlit", "run", "services/ui/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
