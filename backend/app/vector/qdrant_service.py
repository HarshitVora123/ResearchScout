"""Qdrant vector store service — collection management, upsert, and search."""

import uuid
from typing import Any

import structlog
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


# ── Collection Definitions ───────────────────────────
OPPORTUNITIES_COLLECTION = "opportunities"
USER_PROFILES_COLLECTION = "user_profiles"

COLLECTION_CONFIGS = {
    OPPORTUNITIES_COLLECTION: {
        "size": settings.embedding_dimensions,
        "distance": models.Distance.COSINE,
        "on_disk_payload": True,
        "payload_indexes": [
            ("opportunity_type", models.PayloadSchemaType.KEYWORD),
            ("organization", models.PayloadSchemaType.KEYWORD),
            ("country", models.PayloadSchemaType.KEYWORD),
            ("is_active", models.PayloadSchemaType.BOOL),
        ],
    },
    USER_PROFILES_COLLECTION: {
        "size": settings.embedding_dimensions,
        "distance": models.Distance.COSINE,
        "on_disk_payload": True,
        "payload_indexes": [],
    },
}


def get_qdrant_client() -> QdrantClient:
    """Create a Qdrant client instance."""
    return QdrantClient(url=settings.qdrant_url, timeout=30)


class QdrantService:
    """High-level service for Qdrant vector operations."""

    def __init__(self, client: QdrantClient | None = None):
        self.client = client or get_qdrant_client()

    def ensure_collections(self) -> None:
        """Create collections if they don't exist."""
        for name, config in COLLECTION_CONFIGS.items():
            try:
                self.client.get_collection(name)
                logger.info("collection_exists", collection=name)
            except (UnexpectedResponse, Exception):
                self.client.create_collection(
                    collection_name=name,
                    vectors_config=models.VectorParams(
                        size=config["size"],
                        distance=config["distance"],
                        on_disk=True,
                    ),
                    on_disk_payload=config.get("on_disk_payload", True),
                )
                logger.info("collection_created", collection=name)

                # Create payload indexes
                for field_name, field_type in config.get("payload_indexes", []):
                    self.client.create_payload_index(
                        collection_name=name,
                        field_name=field_name,
                        field_schema=field_type,
                    )

    def upsert_opportunity(
        self,
        opportunity_id: str,
        embedding: list[float],
        payload: dict[str, Any],
    ) -> None:
        """Upsert an opportunity vector."""
        self.client.upsert(
            collection_name=OPPORTUNITIES_COLLECTION,
            points=[
                models.PointStruct(
                    id=opportunity_id,
                    vector=embedding,
                    payload=payload,
                )
            ],
        )

    def upsert_user_profile(
        self,
        user_id: str,
        embedding: list[float],
        payload: dict[str, Any],
    ) -> None:
        """Upsert a user profile vector."""
        self.client.upsert(
            collection_name=USER_PROFILES_COLLECTION,
            points=[
                models.PointStruct(
                    id=user_id,
                    vector=embedding,
                    payload=payload,
                )
            ],
        )

    def search_similar_opportunities(
        self,
        query_vector: list[float],
        limit: int = 20,
        score_threshold: float = 0.5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict]:
        """Search for similar opportunities by vector."""
        query_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                if isinstance(value, list):
                    conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchAny(any=value),
                        )
                    )
                elif isinstance(value, bool):
                    conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value),
                        )
                    )
                else:
                    conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value),
                        )
                    )
            query_filter = models.Filter(must=conditions)

        results = self.client.query_points(
            collection_name=OPPORTUNITIES_COLLECTION,
            query=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter,
            with_payload=True,
        )

        return [
            {
                "id": str(point.id),
                "score": point.score,
                "payload": point.payload,
            }
            for point in results.points
        ]

    def search_for_user(
        self,
        user_vector: list[float],
        limit: int = 50,
        score_threshold: float = 0.4,
        exclude_ids: list[str] | None = None,
    ) -> list[dict]:
        """Find opportunities matching a user's profile vector."""
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="is_active",
                    match=models.MatchValue(value=True),
                ),
            ],
        )

        results = self.client.query_points(
            collection_name=OPPORTUNITIES_COLLECTION,
            query=user_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter,
            with_payload=True,
        )

        hits = []
        for point in results.points:
            if exclude_ids and str(point.id) in exclude_ids:
                continue
            hits.append({
                "id": str(point.id),
                "score": point.score,
                "payload": point.payload,
            })

        return hits

    def find_near_duplicates(
        self,
        embedding: list[float],
        threshold: float = 0.92,
        limit: int = 5,
    ) -> list[dict]:
        """Find near-duplicate opportunities by vector similarity."""
        results = self.client.query_points(
            collection_name=OPPORTUNITIES_COLLECTION,
            query=embedding,
            limit=limit,
            score_threshold=threshold,
            with_payload=True,
        )

        return [
            {
                "id": str(point.id),
                "score": point.score,
                "title": point.payload.get("title", ""),
                "organization": point.payload.get("organization", ""),
            }
            for point in results.points
        ]

    def delete_opportunity(self, opportunity_id: str) -> None:
        """Delete an opportunity vector."""
        self.client.delete(
            collection_name=OPPORTUNITIES_COLLECTION,
            points_selector=models.PointIdsList(
                points=[opportunity_id],
            ),
        )

    def collection_count(self, collection_name: str) -> int:
        """Get the number of vectors in a collection."""
        info = self.client.get_collection(collection_name)
        return info.points_count or 0
