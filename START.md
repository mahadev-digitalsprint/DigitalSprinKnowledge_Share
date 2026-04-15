# Quick Start

## 1. Create `.env`
```bash
cp .env.example .env
# Set OPENAI_API_KEY and ANTHROPIC_API_KEY at minimum
```

## 2. Start infrastructure + backend
```bash
docker compose up --build
```

Backend: `http://localhost:8000`  
MinIO console: `http://localhost:9001`

## 3. Start frontend
```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

UI: `http://localhost:3000`

## v3 Ingestion Flow

| Action | What happens |
|--------|--------------|
| Upload document | Local hot parser -> fast chunking -> embed -> Qdrant searchable |
| Complex document | Cold upgrade runs after searchable and replaces fast chunks with premium chunks |
| Ask question | Collection-aware embed route -> Qdrant search by embedding profile -> LLM stream |
| Event stream | SSE only (`/api/chat`, `/api/events`, legacy `/api/events/{doc_id}` kept for compatibility) |

## Registry

The backend now reads runtime defaults from:

`backend/config/registry.yaml`

That file controls:
- default chat/classify/HyDE models
- embedding profiles and Qdrant collection names
- parser hot/cold defaults
- reranker defaults

## Health check
```bash
curl http://localhost:8000/health
```
