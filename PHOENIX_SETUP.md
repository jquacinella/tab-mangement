# Phoenix (Arize) LLM Observability Setup

This document describes the Phoenix observability integration for TabBacklog.

## What is Phoenix?

Phoenix by Arize is an open-source LLM observability platform that provides:
- Real-time tracing of LLM calls
- Token usage and cost tracking
- Latency monitoring
- Error detection and debugging
- Prompt engineering tools

## Integration Overview

Phoenix has been integrated into the TabBacklog enrichment service to automatically trace all DSPy/LLM interactions.

## Files Modified

### 1. `docker-compose.yml`
- Added Phoenix service container (port 6006 for UI, 4317/4318 for OTLP)
- Added Phoenix volume for data persistence
- Updated enrichment service to depend on Phoenix
- Added Phoenix environment variables to enrichment service

### 2. `requirements.txt`
Added Phoenix dependencies:
- `arize-phoenix>=4.0.0` - Phoenix client library
- `openinference-instrumentation-dspy>=0.1.0` - DSPy instrumentation
- `opentelemetry-sdk>=1.20.0` - OpenTelemetry SDK
- `opentelemetry-exporter-otlp>=1.20.0` - OTLP exporter

### 3. `enrichment_service/main.py`
- Added Phoenix/OpenTelemetry imports
- Created `setup_phoenix_tracing()` function
- Integrated tracing setup in application lifespan
- Automatic DSPy instrumentation

### 4. `enrichment_service/Dockerfile`
Added environment variables:
- `OTEL_EXPORTER_OTLP_ENDPOINT=http://phoenix:4317`
- `PHOENIX_PROJECT_NAME=tabbacklog`

### 5. `.env.example`
Added Phoenix configuration section with:
- `OTEL_EXPORTER_OTLP_ENDPOINT` - OpenTelemetry endpoint
- `PHOENIX_COLLECTOR_ENDPOINT` - Phoenix UI endpoint
- `PHOENIX_PROJECT_NAME` - Project identifier

### 6. `README.md`
- Added Phoenix to features list
- Updated Quick Start with Phoenix URL
- Added comprehensive "LLM Observability with Phoenix" section
- Updated environment variables documentation

## How It Works

1. **Startup**: When the enrichment service starts, it initializes Phoenix tracing
2. **Instrumentation**: DSPy is automatically instrumented to send traces
3. **Tracing**: Every LLM call is traced with full context:
   - Input prompts
   - Output completions
   - Token counts
   - Latency
   - Errors
4. **Export**: Traces are sent to Phoenix via OTLP (OpenTelemetry Protocol)
5. **Visualization**: Phoenix UI displays traces in real-time

## Usage

### Starting Services

```bash
# Start all services including Phoenix
docker-compose up -d

# Check Phoenix is running
curl http://localhost:6006/healthz
```

### Accessing Phoenix UI

Open your browser to: http://localhost:6006

### Viewing Traces

1. Navigate to Phoenix UI
2. Select the "tabbacklog" project
3. View traces in the Trace Explorer
4. Analyze metrics in the Analytics dashboard

### Disabling Phoenix

To disable Phoenix tracing (e.g., for development):

```bash
# In .env file
OTEL_EXPORTER_OTLP_ENDPOINT=disabled
```

Or comment out the Phoenix service in `docker-compose.yml`.

## Data Persistence

Phoenix data is stored in the `tabbacklog-phoenix-data` Docker volume. This persists:
- Trace history
- Analytics data
- Project configurations

To reset Phoenix data:

```bash
docker-compose down
docker volume rm tabbacklog-phoenix-data
docker-compose up -d
```

## Troubleshooting

### Phoenix UI not accessible
- Check if Phoenix container is running: `docker ps | grep phoenix`
- Check logs: `docker logs tabbacklog-phoenix`
- Verify port 6006 is not in use: `netstat -an | grep 6006`
- Check health status: `docker compose ps phoenix`

### No traces appearing
- Verify enrichment service is sending traces: `docker logs tabbacklog-enrichment`
- Check for "Phoenix tracing configured successfully" in logs
- Ensure `OTEL_EXPORTER_OTLP_ENDPOINT` is not set to "disabled"
- Verify Phoenix is healthy: `docker compose ps phoenix` (should show "healthy")
- Test by making an enrichment request:
  ```bash
  curl -X POST http://localhost:8002/enrich_tab \
    -H "Content-Type: application/json" \
    -d '{"url": "https://example.com", "title": "Test", "site_kind": "generic_html", "text": "Test content"}'
  ```

### Connection errors
- Ensure enrichment service can reach Phoenix: `docker exec tabbacklog-enrichment ping phoenix`
- Check network configuration in docker-compose.yml
- Verify both services are on the same network (`tabbacklog-network`)
- Check that OTLP endpoint uses service name: `http://phoenix:4317` (not `localhost`)

### Health check failures
If Phoenix health check is failing:
- Check if Python is available in container: `docker exec tabbacklog-phoenix python3 --version`
- Verify health check endpoint: `docker exec tabbacklog-phoenix curl http://localhost:6006/healthz`
- Review health check configuration in docker-compose.yml

### Database connection issues
If services can't connect to PostgreSQL:
- Ensure DATABASE_URL uses service name `postgres` not `localhost`
- Example: `postgresql://postgres:postgres@postgres:5432/tabbacklog`
- For local development outside Docker, use `localhost` instead
- Check that postgres service is healthy: `docker compose ps postgres`

## Benefits

1. **Debugging**: See exactly what prompts are sent and responses received
2. **Optimization**: Identify slow LLM calls and optimize prompts
3. **Cost Tracking**: Monitor token usage to estimate API costs
4. **Quality Assurance**: Catch errors and unexpected outputs
5. **Experimentation**: Compare different prompt strategies

## Next Steps

- Explore Phoenix dashboards to understand LLM behavior
- Set up alerts for high latency or error rates
- Use Phoenix to optimize prompts for better results
- Export traces for further analysis

## Resources

- [Phoenix Documentation](https://docs.arize.com/phoenix)
- [OpenInference Specification](https://github.com/Arize-ai/openinference)
- [DSPy Documentation](https://dspy-docs.vercel.app/)
