# User Guide

## Quick Start

### 1. Setup Environment

```bash
# Install dependencies
uv sync

# Start services
docker compose up -d

# Run migrations
python src/database/migrations_tickets.py

# Initialize KB
python scripts/init_sample_kb.py
```

### 2. Configure

Add to `.env`:

```env
# Twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# OpenAI
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o-mini

# ElevenLabs
ELEVENLABS_API_KEY=your_elevenlabs_key

# Jira (optional)
JIRA_SERVER=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=YOUR_PROJECT_KEY

# Database
DATABASE_URL=postgresql://user:pass@localhost:5436/qualifybot

# Redis
REDIS_URL=redis://localhost:6383
```

### 3. Start Server

```bash
# Development
uvicorn src.main:app --reload --port 10000

# Production
docker compose up
```

### 4. Configure Twilio Webhook

Set webhook URL in Twilio Console:
```
https://your-domain.com/twilio/webhook
```

## API Endpoints

### Health Check
```
GET /health
```

### Analytics
```
GET /api/v1/analytics/metrics?days=30
GET /api/v1/analytics/common-issues?days=30
```

### KB Management
```
POST /api/v1/kb/ingest
GET /api/v1/kb/documents
DELETE /api/v1/kb/documents/{doc_id}
```

## Knowledge Base

### Add Documents

```bash
# Via API
curl -X POST http://localhost:10000/api/v1/kb/ingest \
  -F "file=@printer_guide.pdf" \
  -F "tenant_id=default" \
  -F "category=hardware"
```

### Supported Formats
- PDF
- DOCX
- Markdown (.md)
- Text (.txt)

## Monitoring

### View Conversations
```
conversations/{call_sid}/summary.md
conversations/{call_sid}/transcript.json
```

### Database Queries
```sql
-- Recent tickets
SELECT * FROM support_tickets ORDER BY created_at DESC LIMIT 10;

-- Resolution rate
SELECT 
  COUNT(*) FILTER (WHERE status = 'resolved') * 100.0 / COUNT(*) as resolution_rate
FROM support_tickets;
```

