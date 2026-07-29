"""FastAPI application factory — main entry point for ResearchScout API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.config import get_settings
from app.core.exceptions import ResearchScoutError
from app.models.schemas.common import HealthResponse

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — startup and shutdown hooks."""
    # Startup
    from app.core.logging import setup_logging

    setup_logging()

    import structlog
    logger = structlog.get_logger(__name__)
    logger.info("app_starting", app=settings.app_name, env=settings.app_env)

    # Initialize Qdrant collections
    try:
        from app.vector.qdrant_service import QdrantService
        qdrant = QdrantService()
        qdrant.ensure_collections()
        logger.info("qdrant_initialized")
    except Exception as e:
        logger.warning("qdrant_init_failed", error=str(e))

    # Initialize Neo4j schema
    try:
        from app.knowledge_graph.neo4j_service import Neo4jService
        neo4j = Neo4jService()
        await neo4j.init_schema()
        await neo4j.close()
        logger.info("neo4j_initialized")
    except Exception as e:
        logger.warning("neo4j_init_failed", error=str(e))

    yield
    # Shutdown
    logger.info("app_shutting_down", app=settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description=(
        "AI Agent platform for autonomous research opportunity discovery. "
        "Discovers, extracts, verifies, ranks, and recommends research "
        "opportunities from the global internet."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",    # Next.js dev
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception Handlers ───────────────────────────────

@app.exception_handler(ResearchScoutError)
async def researchscout_error_handler(request: Request, exc: ResearchScoutError):
    """Handle custom ResearchScout exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


# ── Routes ───────────────────────────────────────────

app.include_router(v1_router)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.get("/metrics", tags=["Observability"])
async def metrics():
    """Prometheus metrics endpoint."""
    from app.core.metrics import metrics_endpoint
    return metrics_endpoint()


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint returning API metadata."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
    }
