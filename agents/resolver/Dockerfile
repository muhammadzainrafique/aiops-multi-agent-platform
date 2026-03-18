FROM python:3.11-slim

WORKDIR /app

COPY shared/ ./shared/

COPY agents/resolver/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/resolver/ ./agents/resolver/

ENV PYTHONPATH=/app

CMD ["python", "agents/resolver/main.py"]
