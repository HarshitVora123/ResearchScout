# ResearchScout Backend

FastAPI backend service for ResearchScout AI platform.

## Local development

From the repository root, configure `.env` using `.env.example` and start the backing services:

```bash
docker compose up -d postgres redis qdrant neo4j
cd backend
pip install -e ".[dev]" aiosqlite
alembic upgrade head
uvicorn app.main:app --reload
```

Run the Celery queues in separate terminals:

```bash
celery -A app.workers.celery_app worker -l info -Q default,extract,embed
celery -A app.workers.celery_app worker -l info -Q crawl
celery -A app.workers.celery_app beat -l info
```

Search and model API credentials enable discovery and vector features. Without them, search may return no results and vector operations remain unavailable.
