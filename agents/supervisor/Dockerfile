FROM python:3.11-slim

WORKDIR /app

# Copy shared layer first — maximises Docker build cache reuse
COPY shared/ ./shared/

COPY agents/supervisor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/supervisor/ ./agents/supervisor/

ENV PYTHONPATH=/app
EXPOSE 5001

CMD ["python", "agents/supervisor/main.py"]
