FROM python:3.13-slim

WORKDIR /app

# Copy shared models first
COPY shared-models /app/shared-models

# Install shared models
RUN pip install -e /app/shared-models

# Copy service files
COPY event-processor/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

COPY event-processor/app.py .

CMD ["python", "app.py"]
