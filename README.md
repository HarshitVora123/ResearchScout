# 🔬 ResearchScout

**AI-Powered Research Opportunity Discovery Platform**

ResearchScout uses 20+ autonomous AI agents to discover, extract, verify, rank, and recommend research opportunities — PhD positions, internships, fellowships, scholarships, and more — from thousands of sources worldwide.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌───────────┐
│  Next.js UI  │ ──→ │  FastAPI API  │ ──→ │  AI Agents   │ ──→ │  Storage  │
│  (React 19)  │     │  (Python 3.12)│     │  (LangGraph) │     │  (5 DBs)  │
└─────────────┘     └──────────────┘     └──────────────┘     └───────────┘
```

**Frontend:** Next.js 15 (App Router) · TypeScript · TailwindCSS  
**Backend:** FastAPI · SQLAlchemy (async) · Celery · structlog  
**Agents:** LangGraph · Gemini 2.5 Flash · GPT-4o · spaCy  
**Storage:** PostgreSQL · Redis · Qdrant (vectors) · Neo4j (graph) · MinIO  
**Infra:** Docker Compose · GitHub Actions CI · Alembic migrations  

## Quick Start

### 1. Clone & Configure

```bash
git clone https://github.com/your-org/researchscout.git
cd researchscout
cp .env.example .env       # Edit with your API keys
cp frontend/.env.local.example frontend/.env.local
```

### 2. Start Infrastructure

```bash
docker compose up -d postgres redis qdrant neo4j
```

### 3. Run Backend

```bash
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

### 4. Run Workers

```bash
# In separate terminals:
celery -A app.workers.celery_app worker -l info -Q default,extract
celery -A app.workers.celery_app worker -l info -Q crawl
celery -A app.workers.celery_app beat -l info
```

### 5. Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) (frontend) and [http://localhost:8000/docs](http://localhost:8000/docs) (API docs).

## Discovery Pipeline

```
Query Generator → Search Agent → Rate Limiter → Crawler → Content Cleaner
                                                               ↓
PostgreSQL ← Dedup ← Validator ← NLP Enrichment ← LLM Extractor
```

1. **Query Generator** — Creates targeted queries for 8 opportunity types across 5 academic sites
2. **Search Agent** — Multi-engine search (Google CSE + Bing + Tavily)
3. **Crawler** — Rate-limited HTTP fetching with robots.txt compliance
4. **Content Cleaner** — HTML → markdown with boilerplate stripping
5. **NLP Pre-filter** — Rule-based opportunity detection (14 regex patterns)
6. **LLM Extractor** — Gemini Flash / GPT-4o structured extraction
7. **Validator** — 6-check validation (domain trust, scam detection, hallucination detection)
8. **Dedup** — Source URL + title+org deduplication
9. **Storage** — PostgreSQL with 35+ fields per opportunity

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | User registration |
| POST | `/api/v1/auth/login` | JWT login |
| GET | `/api/v1/opportunities` | List with filters & pagination |
| GET | `/api/v1/opportunities/{id}` | Opportunity detail |
| POST | `/api/v1/pipeline/discover` | Trigger AI discovery |
| POST | `/api/v1/pipeline/crawl/url` | Crawl a single URL |
| POST | `/api/v1/pipeline/sources/seed` | Load seed sources |

## Testing

```bash
cd backend
pytest tests/ -v --cov=app
```

## Project Structure

```
researchscout/
├── frontend/          # Next.js 15 + TypeScript
│   └── src/
│       ├── app/       # Pages (landing, auth, opportunities, dashboard)
│       ├── components/ # Reusable UI (Navbar, OpportunityCard)
│       └── lib/       # API client, auth context, utilities
├── backend/
│   └── app/
│       ├── agents/    # AI agents (search, crawl, extract, validate, orchestrator)
│       ├── api/       # REST endpoints (auth, users, opportunities, pipeline)
│       ├── core/      # Database, security, logging, Redis
│       ├── models/    # ORM models + Pydantic schemas
│       ├── nlp/       # Keyword extraction, deadline parsing, skill extraction
│       ├── services/  # Business logic (opportunity CRUD, crawl sources)
│       └── workers/   # Celery tasks (crawl, extract, embed, notify)
├── data/seed/         # 55 curated crawl sources
└── docker-compose.yml # 8-service infrastructure
```

## License

MIT
