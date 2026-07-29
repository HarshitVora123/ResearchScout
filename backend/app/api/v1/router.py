"""API v1 root router — aggregates all endpoint routers."""

from fastapi import APIRouter

from app.api.v1 import assist, auth, graph, notifications, opportunities, pipeline, search, users

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(users.router, prefix="/users", tags=["Users"])
router.include_router(opportunities.router, prefix="/opportunities", tags=["Opportunities"])
router.include_router(pipeline.router, prefix="/pipeline", tags=["Pipeline Admin"])
router.include_router(graph.router)
router.include_router(search.router)
router.include_router(notifications.router)
router.include_router(assist.router)

