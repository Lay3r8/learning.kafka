FROM python:3.13-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl

# Clear cached package lists
RUN rm -rf /var/lib/apt/lists/*

# Copy shared models first
COPY shared-models /app/shared-models

# Install shared models
RUN pip install -e /app/shared-models

# Copy service files
COPY query-service/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

COPY query-service/app.py .

EXPOSE 5001

CMD ["python", "app.py"]
