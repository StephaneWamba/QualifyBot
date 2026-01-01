# IT Support Voice Assistant - Documentation

## Problem

IT support teams are overwhelmed with repetitive calls for common issues (printer problems, email setup, WiFi connectivity). Manual support is:

- **Expensive**: Requires 24/7 staff
- **Slow**: Long wait times
- **Inefficient**: Same issues resolved repeatedly

## Solution

Automated voice assistant that:

- Answers calls 24/7
- Provides step-by-step troubleshooting
- Retrieves solutions from knowledge base
- Escalates complex issues to humans
- Creates tickets automatically in Jira

## Architecture

```mermaid
graph TB
    User[User Calls] --> Twilio[Twilio Voice]
    Twilio --> Webhook[FastAPI Webhook]
    Webhook --> Orchestrator[Support Orchestrator]
    Orchestrator --> Graph[LangGraph Agent]
    Graph --> LLM[OpenAI GPT-4o-mini]
    Graph --> KB[KB Retrieval RAG]
    Graph --> Jira[Jira Service]
    Graph --> DB[(PostgreSQL)]
    Graph --> TTS[ElevenLabs TTS]
    KB --> ChromaDB[(ChromaDB)]
    Graph --> Logger[Conversation Logger]
    TTS --> Twilio
```

## Documentation

- [User Guide](./user-guide.md) - How to use the system
- [Architecture](./architecture.md) - System design and components
