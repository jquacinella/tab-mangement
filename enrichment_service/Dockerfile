FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy enrichment service code
COPY enrichment_service/ ./enrichment_service/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Environment variables (override in docker-compose or at runtime)
ENV LLM_API_BASE=http://localhost:1234/v1
ENV LLM_API_KEY=dummy_key
ENV LLM_MODEL_NAME=llama-3.1-8b-instruct
ENV LLM_TIMEOUT=60
ENV MAX_RETRIES=3

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8002/health').raise_for_status()"

# Run the service
CMD ["uvicorn", "enrichment_service.main:app", "--host", "0.0.0.0", "--port", "8002"]
