# QualifyBot Implementation Roadmap

**Project**: Sales Qualification Voice Bot  
**NFRs**: Accuracy, Low Latency, Maintainability, Modularity  
**Package Manager**: uv  
**CRM**: Salesforce  
**LLM**: OpenAI GPT-4o-mini

---

## Phase 1: Foundation (Week 1-2)

### 1.1 Project Setup

- [x] Initialize project structure with uv
- [x] Setup FastAPI backend skeleton
- [x] Configure Docker with multi-stage builds (fast builds)
- [x] Setup development environment (Docker Compose)
- [x] Initialize Git repo, create develop branch
- [ ] Setup CI/CD basics (GitHub Actions)

### 1.2 Core Infrastructure

- [ ] Twilio Voice integration (webhook handling)
- [ ] OpenAI Realtime API integration (STT only)
- [ ] ElevenLabs TTS integration
- [ ] Redis setup (session state)
- [ ] PostgreSQL setup (qualification data)
- [ ] Environment configuration management

### 1.3 Basic Call Flow

- [ ] Incoming call webhook handler
- [ ] Audio streaming setup (Twilio → Backend)
- [ ] STT pipeline (OpenAI Realtime → text)
- [ ] TTS pipeline (text → ElevenLabs → audio)
- [ ] Basic conversation loop (greeting → response)

**Deliverable**: End-to-end call flow (call → AI speaks → responds)

---

## Phase 2: Qualification Logic (Week 3-4)

### 2.1 State Machine

- [ ] Design Q&A state machine (6 questions)
- [ ] Implement state transitions
- [ ] Session state persistence (Redis)
- [ ] State recovery on reconnection

### 2.2 Question Flow

- [ ] Question 1: Company size (extraction logic)
- [ ] Question 2: Budget range (NER, validation)
- [ ] Question 3: Timeline (date parsing)
- [ ] Question 4: Decision makers (entity extraction)
- [ ] Question 5: Current solution (classification)
- [ ] Question 6: Primary use case (intent detection)

### 2.3 Data Extraction

- [ ] GPT-4o-mini integration for extraction
- [ ] Structured data validation
- [ ] Non-answer detection
- [ ] Partial answer handling

**Deliverable**: Complete 6-question flow with data extraction

---

## Phase 3: CRM Integration (Week 5)

### 3.1 Salesforce Integration

- [ ] Salesforce API client setup
- [ ] Authentication (OAuth2)
- [ ] Lead creation endpoint
- [ ] Data mapping (extracted data → Salesforce fields)
- [ ] Error handling and retries

### 3.2 Summarization

- [ ] Conversation summarization (GPT-4o-mini)
- [ ] Structured summary generation
- [ ] Summary → Salesforce notes field

**Deliverable**: Automatic lead creation in Salesforce

---

## Phase 4: Production Readiness (Week 6-7)

### 4.1 Error Handling

- [ ] Comprehensive error handling
- [ ] Graceful degradation
- [ ] Retry logic (exponential backoff)
- [ ] Fallback responses

### 4.2 Monitoring & Observability

- [ ] Sentry integration
- [ ] Custom metrics (latency, accuracy)
- [ ] Logging structure
- [ ] Health checks

### 4.3 Performance Optimization

- [ ] Latency optimization (caching, async)
- [ ] Response time monitoring
- [ ] Database query optimization
- [ ] Redis caching strategy

### 4.4 Testing

- [ ] Unit tests (core logic)
- [ ] Integration tests (Twilio, Salesforce)
- [ ] End-to-end tests (full call flow)
- [ ] Load testing

**Deliverable**: Production-ready system

---

## Phase 5: Polish & Documentation (Week 8)

### 5.1 Documentation

- [ ] API documentation
- [ ] Architecture diagrams
- [ ] Deployment guide
- [ ] Configuration guide

### 5.2 Portfolio Materials

- [ ] Case study write-up
- [ ] Technical deep dive
- [ ] Demo video script
- [ ] Metrics dashboard

**Deliverable**: Complete portfolio project

---

## Technical Architecture

```
Phone Call → Twilio → FastAPI Backend
                      ├─ OpenAI Realtime API (STT)
                      ├─ GPT-4o-mini (extraction, summarization)
                      ├─ ElevenLabs (TTS)
                      ├─ Redis (session state)
                      ├─ PostgreSQL (qualification data)
                      └─ Salesforce API (lead creation)
```

---

## Key Modules

### Core Modules

- `call_handler.py` - Twilio webhook handling
- `stt_service.py` - OpenAI Realtime STT integration
- `tts_service.py` - ElevenLabs TTS integration
- `state_machine.py` - Q&A flow state management
- `extraction_service.py` - Data extraction from conversation
- `crm_client.py` - Salesforce integration
- `session_manager.py` - Redis session management

### Supporting Modules

- `config.py` - Configuration management
- `logging.py` - Structured logging
- `monitoring.py` - Metrics and observability
- `errors.py` - Error handling
- `models.py` - Data models (Pydantic)
- `database.py` - PostgreSQL connection

---

## Docker Optimization Strategy

### Multi-stage Builds

```dockerfile
# Stage 1: Dependencies
FROM python:3.12-slim as deps
RUN pip install uv
COPY pyproject.toml ./
RUN uv sync --frozen

# Stage 2: Application
FROM python:3.12-slim
COPY --from=deps /app/.venv /app/.venv
COPY . /app
```

### Build Cache Optimization

- Layer dependencies separately
- Use .dockerignore
- Cache uv dependencies
- Parallel builds where possible

---

## Success Metrics

### Accuracy

- Data extraction accuracy: >95%
- Intent detection accuracy: >90%
- CRM lead creation success: >99%

### Latency

- STT latency: <500ms
- TTS latency: <800ms
- End-to-end response: <2s

### Maintainability

- Code coverage: >80%
- Modular architecture (clear separation)
- Comprehensive documentation
