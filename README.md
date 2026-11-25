# 🔬 ResearchScout

**Research opportunities, easier to find.**

ResearchScout helps you search research openings, review source links, and keep relevant roles in one place. Discovery sources and optional language-model features depend on the credentials you configure; the app does not ship with provider credentials or a private opportunity feed.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌───────────┐
│  Next.js UI  │ ──→ │  FastAPI API  │ ──→ │  AI Agents   │ ──→ │  Storage  │
│  (React 19)  │     │  (Python 3.12)│     │  (workers)   │     │  (4 stores)│
└─────────────┘     └──────────────┘     └──────────────┘     └───────────┘
```

- **Frontend:** Next.js 16 (App Router) · React 19 · TypeScript · TailwindCSS
- **Backend:** FastAPI · SQLAlchemy (async) · Celery · structlog
- **Discovery:** Configurable search providers · optional Gemini / OpenAI extraction · rule-based NLP
- **Storage:** PostgreSQL · Redis/Celery · Qdrant (vectors) · Neo4j (graph)
- **Infra:** Docker Compose · GitHub Actions CI · Alembic migrations

## Quick Start

### 1. Clone & Configure

```bash
Copy `.env.example` to `.env` and `frontend/.env.local.example` to `frontend/.env.local`. Add search provider credentials if you want discovery to fetch new listings; extraction providers are optional. Without provider credentials, you can run the app and use existing records, but external discovery is limited.
```

### 2. Start the full project

```bash
docker compose up --build
```

Compose starts the databases, API, background workers, scheduler, and frontend. Open [http://localhost:3000](http://localhost:3000) (frontend) and [http://localhost:8000/docs](http://localhost:8000/docs) (API docs). Use `docker compose down` to stop the services. On PowerShell, this single command creates missing local env files and starts the stack:

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }; if (!(Test-Path frontend/.env.local)) { Copy-Item frontend/.env.local.example frontend/.env.local }; docker compose up --build
```

Docker Desktop must be running first. This starts the app with development defaults; configure real search provider credentials in `.env` for external discovery.

### Backups

PostgreSQL is the durable source of truth. Create a custom-format dump with `./scripts/backup.ps1`; dumps are written under `backups/` and excluded from Git. Restore a dump with `./scripts/restore.ps1 -Backup ./backups/<filename>.dump -Confirm`. Restore replaces database contents and stops the API/workers first. Redis contains transient queues; vector and graph indexes can be recreated from PostgreSQL records.

## Discovery Pipeline

```
Query Generator → Search Agent → Rate Limiter → Crawler → Content Cleaner
                                                               ↓
PostgreSQL ← Dedup ← Validator ← NLP Enrichment ← LLM Extractor
```

1. **Query Generator** — Creates targeted queries for 8 opportunity types across 5 academic sites
2. **Search Agent** — Multi-engine search (Google CSE + Bing + Tavily, when configured)
3. **Crawler** — Rate-limited HTTP fetching with robots.txt compliance
4. **Content Cleaner** — HTML → markdown with boilerplate stripping; JavaScript rendering is not currently implemented
5. **NLP Pre-filter** — Rule-based opportunity detection (14 regex patterns)
6. **Extractor** — Deterministic extraction runs first; Gemini / OpenAI are optional fallbacks
7. **Validator** — Heuristic validation for URL shape, domain reputation, deadlines, completeness, scam indicators, and text overlap
8. **Dedup** — Source URL + title+org deduplication
9. **Storage** — PostgreSQL; vector and graph indexing run in Celery workers when configured

Production Compose requires `SECRET_KEY`, `ADMIN_API_KEY`, `CORS_ORIGINS`, `POSTGRES_PASSWORD`, and `NEO4J_PASSWORD`. Set `CORS_ORIGINS` as a JSON array, for example `["https://app.example.com"]`, use unique production secrets, and configure the API credentials your deployment needs.

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
├── frontend/          # Next.js + TypeScript
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
