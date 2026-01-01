# QualifyBot

**IT Support Voice Assistant** - Automated IT helpdesk support via phone calls.

## Overview

QualifyBot automates IT support through intelligent voice conversations. It helps users troubleshoot issues, retrieves relevant knowledge base articles, and creates support tickets in Jira when escalation is needed.

## Features

- **Intelligent Troubleshooting**: RAG-powered knowledge base retrieval
- **Natural Conversations**: Human-like voice interactions with ElevenLabs TTS
- **Automatic Ticket Creation**: Creates Jira tickets on escalation
- **Multi-tenant Support**: Isolated knowledge bases per tenant
- **Low Latency**: <2s end-to-end response time
- **Production Ready**: Error handling, monitoring, observability

## Tech Stack

- **PSTN**: Twilio Voice
- **STT**: OpenAI Realtime API
- **TTS**: ElevenLabs
- **LLM**: OpenAI GPT-4o-mini
- **RAG**: ChromaDB with OpenAI embeddings
- **Ticketing**: Jira
- **Backend**: FastAPI (Python)
- **State**: Redis (LangGraph checkpoints)
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
│   ├── core/          # Core services (STT, TTS, config, logging)
│   ├── agent/         # LangGraph agent (nodes, state, orchestrator)
│   ├── services/      # Business logic (Jira, KB, tickets, escalation)
│   ├── database/      # Database models and migrations
│   └── api/           # FastAPI routes
├── knowledge_base/    # Sample knowledge base documents
├── tests/
└── docker/
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

