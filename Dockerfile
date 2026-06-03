FROM python:3.10-slim

# Create user to run the container (Hugging Face runs as non-root user with UID 1000)
RUN useradd -m -u 1000 user
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy all application files
COPY --chown=user:1000 . .

# Run database schema initialization and ML pipelines to pre-populate data
RUN python3 db/init_db.py && \
    python3 src/data_generator.py && \
    python3 src/anomaly_detector.py && \
    python3 src/audit_agent.py && \
    python3 src/export_data.py

# Switch to the non-root user
USER user

# Hugging Face Spaces defaults to port 7860
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "7860"]
