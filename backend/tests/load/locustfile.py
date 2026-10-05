from typing import Any

try:
    from locust import HttpUser, between, task
except ImportError:
    # Safe fallback definitions for IDE linters when running standalone
    class HttpUser:  # type: ignore
        client: Any

    def task(weight: int = 1):  # type: ignore
        def decorator(f):
            return f
        return decorator

    def between(a: float, b: float):  # type: ignore
        return 1


class ResearchScoutUser(HttpUser):
    """Simulated user interacting with ResearchScout API."""

    wait_time = between(1, 3)

    @task(3)
    def view_opportunities(self):
        """Simulate browsing opportunities feed."""
        self.client.get("/api/v1/opportunities?page_size=10")

    @task(2)
    def semantic_search(self):
        """Simulate semantic search query."""
        self.client.get("/api/v1/search/semantic?q=machine+learning+phd")

    @task(2)
    def graph_stats(self):
        """Simulate viewing knowledge graph statistics."""
        self.client.get("/api/v1/graph/stats")

    @task(1)
    def health_check(self):
        """Check system health."""
        self.client.get("/health")

