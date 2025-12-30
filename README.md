# QualifyBot

**Sales Qualification Voice Bot** - Automated B2B lead qualification via phone calls.

## Overview

QualifyBot automates sales qualification through structured voice conversations. It asks 6 key questions, extracts data, and creates leads in Salesforce automatically.

## Features

- **Structured Q&A Flow**: 6-question qualification process
- **Data Extraction**: Automatic extraction from natural speech
- **Salesforce Integration**: Real-time lead creation
- **Human-like Voice**: ElevenLabs TTS for natural conversations
- **Low Latency**: <2s end-to-end response time
- **Production Ready**: Error handling, monitoring, observability

## Tech Stack

- **PSTN**: Twilio Voice
- **STT**: OpenAI Realtime API
- **TTS**: ElevenLabs
- **LLM**: OpenAI GPT-4o-mini
- **CRM**: Salesforce
- **Backend**: FastAPI (Python)
- **State**: Redis
- **Database**: PostgreSQL
- **Package Manager**: uv

## Quick Start

```bash
# Install dependencies
make install

# Start services (Redis, PostgreSQL)
make docker-up

# Start dev server
make dev

# Health check
curl http://localhost:10000/health
```

See [ROADMAP.md](./ROADMAP.md) for implementation plan.

## Ports

- **API**: 10000 (mapped from container 8000)
- **Redis**: 6383 (mapped from container 6379)
- **PostgreSQL**: 5436 (mapped from container 5432)

## Project Structure

```
QualifyBot/
├── src/
│   ├── core/          # Core services (STT, TTS, state)
│   ├── crm/           # Salesforce integration
│   ├── extraction/    # Data extraction logic
│   └── api/           # FastAPI routes
├── tests/
├── docker/
└── docs/
```

## Deployment

### Railway

See [RAILWAY.md](./RAILWAY.md) for detailed Railway deployment instructions.

Quick steps:
1. Push code to GitHub
2. Create Railway project from GitHub repo
3. Add PostgreSQL and Redis services
4. Configure environment variables
5. Deploy!

## Development

Work in `develop` branch only.

## License

MIT

