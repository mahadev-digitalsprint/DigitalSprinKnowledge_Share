# Quick Start

## 1. Create `.env`
```bash
cp .env.example .env
# Set OPENAI_API_KEY
```

## 2. Start the backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
cd ..
uvicorn app.main:app --app-dir backend
```

Backend: `http://localhost:8000`

**Python note:** 3.12 or 3.13 recommended. 3.14 works but only with the current pydantic pins.

**Local data stored in:**
- `backend/data/app.db`
- `backend/data/qdrant`
- `backend/data/storage`

**Dev notes:**
- Embedded Qdrant is single-process — stop any old backend process before starting a new one.
- On Windows, `--reload` can contend for `backend/data/qdrant` and trigger a lock error; omit it.

## 3. Start the frontend
```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

UI: `http://localhost:3000`

## Stack

| Layer | Technology |
|-------|-----------|
| Chat | OpenAI API |
| App data | SQLite (`backend/data/app.db`) |
| Vector search | Embedded Qdrant |
| File storage | Local (`backend/data/storage`) |
| Frontend | Next.js 14 |

No Docker, Postgres, or MinIO required.

## Configuration

Edit `backend/config/registry.yaml` to change:
- Default chat model
- Embedding profile

## Health check
```bash
curl http://localhost:8000/health
```

## Folder structure
```
Tool_Knowledge_RAG/
├── backend/
│   ├── .venv/            # Python virtual environment
│   ├── app/              # FastAPI application
│   ├── config/           # registry.yaml
│   ├── data/             # SQLite + Qdrant + uploads (git-ignored)
│   ├── scripts/          # Seed / reset scripts
│   └── requirements.txt
├── frontend/
│   ├── app/              # Next.js pages
│   ├── components/       # React components
│   ├── lib/              # Utilities and types
│   ├── public/           # Static assets
│   └── styles/           # Global CSS
├── .env.example
└── START.md
```
