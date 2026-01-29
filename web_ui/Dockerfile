FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy web UI code
COPY web_ui/ ./web_ui/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Environment variables
ENV DATABASE_URL=""
ENV DEFAULT_USER_ID=""
ENV APP_SECRET_KEY=""

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

# Run the service
CMD ["uvicorn", "web_ui.main:app", "--host", "0.0.0.0", "--port", "8000"]
