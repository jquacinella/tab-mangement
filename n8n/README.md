# TabBacklog n8n Workflows

This directory contains n8n workflow definitions for orchestrating the TabBacklog pipeline.

## Main Workflow: enrich_tabs.json

Processes new tabs through the fetch/parse and LLM enrichment pipeline.

### Workflow Steps

```
┌─────────────────┐
│  Cron Trigger   │  Every 10 minutes
│  (Schedule)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Get New Tabs   │  SELECT * FROM tab_item WHERE status = 'new' LIMIT 10
│  (Postgres)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Split In Batches│  Process 2 at a time
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Set Fetch       │  UPDATE status = 'fetch_pending'
│ Pending         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Call Parser     │  POST /fetch_parse
│ Service         │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Success?│
    └────┬────┘
    Yes  │  No
    ▼    │    ▼
┌────────┴──┐  ┌─────────────┐
│ Insert    │  │ Set Fetch   │
│ Parsed    │  │ Error       │
└────┬──────┘  └─────────────┘
     │
     ▼
┌─────────────────┐
│ Set LLM Pending │  UPDATE status = 'llm_pending'
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Call Enrichment │  POST /enrich_tab
│ Service         │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Success?│
    └────┬────┘
    Yes  │  No
    ▼    │    ▼
┌────────┴───────┐  ┌─────────────┐
│ Upsert         │  │ Set LLM     │
│ Enrichment     │  │ Error       │
│ + History      │  └─────────────┘
│ + Tags         │
└────┬───────────┘
     │
     ▼
┌─────────────────┐
│ Set Enriched    │  UPDATE status = 'enriched'
└─────────────────┘
```

### Status Flow

```
new → fetch_pending → parsed → llm_pending → enriched
                  ↘            ↘
               fetch_error   llm_error
```

## Setup Instructions

### 1. Configure n8n Credentials

Create a PostgreSQL credential in n8n with name `TabBacklog Postgres`:
- Host: `postgres` (Docker service name) or your database host
- Database: `tabbacklog`
- User: Your database user (default: `postgres`)
- Password: Your database password (default: `postgres`)
- Port: `5432`

**Note:** When running in Docker, use the service name `postgres` as the host, not `localhost`.

### 2. Set Environment Variables

The workflow uses these environment variables (automatically set in docker-compose.yml):
- `PARSER_SERVICE_URL`: URL of the parser service (default: `http://parser:8001`)
- `ENRICHMENT_SERVICE_URL`: URL of the enrichment service (default: `http://enrichment:8002`)

These are configured in the `.env` file and passed to n8n via docker-compose.

### 3. Import the Workflow

1. Open n8n web interface
2. Go to Workflows → Import from File
3. Select `workflows/enrich_tabs.json`
4. Update the PostgreSQL credential reference
5. Activate the workflow

## Manual Trigger

To test the workflow manually:
1. Open the workflow in n8n
2. Click "Execute Workflow"
3. Check the execution log for results

## Customization

### Batch Size

Edit the "Set Config" node to change `batch_size` (default: 10)

### Schedule

Edit the "Every 10 Minutes" node to change the cron interval

### Concurrency

Edit the "Split In Batches" node to change `batchSize` (default: 2)

## Troubleshooting

### Workflow not triggering
- Check that the workflow is activated (toggle in top right)
- Verify n8n has correct timezone settings
- Check n8n logs: `docker compose logs n8n`

### Database connection errors
- Verify PostgreSQL credentials in n8n
- Ensure host is set to `postgres` (Docker service name), not `localhost`
- Check network connectivity: `docker exec tabbacklog-n8n ping postgres`
- Verify postgres is healthy: `docker compose ps postgres`

### Parser/Enrichment errors
- Check service health endpoints:
  ```bash
  curl http://localhost:8001/health  # parser
  curl http://localhost:8002/health  # enrichment
  ```
- Review service logs:
  ```bash
  docker compose logs parser
  docker compose logs enrichment
  ```
- Errors are logged to `event_log` table
- Verify services are healthy: `docker compose ps`

### Service URLs not resolving
- Ensure PARSER_SERVICE_URL and ENRICHMENT_SERVICE_URL use Docker service names
- Correct: `http://parser:8001` and `http://enrichment:8002`
- Wrong: `http://localhost:8001` (won't work inside Docker network)

## Monitoring

Query recent events:
```sql
SELECT * FROM event_log
WHERE event_type LIKE '%error%'
ORDER BY created_at DESC
LIMIT 20;
```

Check pipeline status:
```sql
SELECT status, COUNT(*)
FROM tab_item
WHERE deleted_at IS NULL
GROUP BY status;
```
