# Quick Start

## 1. Create `.env`
```bash
cp .env.example .env
# Set OPENAI_API_KEY
```

## 2. Start the backend

**Kill port 8000 first (Windows):**
```powershell
# PowerShell — kill anything on port 8000
$pids = (netstat -ano | Select-String ":8000\s" | ForEach-Object { ($_ -split '\s+')[-1] } | Sort-Object -Unique)
$pids | ForEach-Object { taskkill /PID $_ /F }
```

**Setup venv (first time only):**
```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

**Run backend:**
```powershell
# From repo root, with root-level venv active
$env:PYTHONPATH="backend"; python -m uvicorn app.main:app --port 
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
- Use `python -m uvicorn` (not bare `uvicorn`) to avoid launcher path errors on Windows.

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
```8000

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
