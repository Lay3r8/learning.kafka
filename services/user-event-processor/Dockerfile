FROM python:3.13.1-slim

WORKDIR /app

# Install dependencies
COPY user-event-processor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY user-event-processor/app.py .

# Run the processor
CMD ["python", "app.py"]
