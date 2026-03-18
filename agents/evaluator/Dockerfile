FROM python:3.11-slim

WORKDIR /app

COPY shared/ ./shared/

COPY agents/evaluator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/evaluator/ ./agents/evaluator/

ENV PYTHONPATH=/app

CMD ["python", "agents/evaluator/main.py"]
