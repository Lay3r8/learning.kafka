FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY user-service/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

# Copy application code
COPY user-service/app.py .

# Expose port
EXPOSE 5002

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5002"]
