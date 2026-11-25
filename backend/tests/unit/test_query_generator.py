"""Unit tests for the search query generator."""

from app.agents.discovery.query_generator import (
    generate_monitoring_queries,
    generate_search_queries,
)


class TestQueryGenerator:
    """Test search query generation."""

    def test_generates_queries(self):
        queries = generate_search_queries(
            topics=["NLP"],
            opportunity_types=["PhD"],
        )
        assert len(queries) > 0
        assert any("NLP" in q for q in queries)
        assert any("PhD" in q.lower() or "phd" in q.lower() for q in queries)

    def test_multiple_topics(self):
        queries = generate_search_queries(
            topics=["NLP", "Computer Vision"],
            opportunity_types=["PhD"],
        )
        assert any("NLP" in q for q in queries)
        assert any("Computer Vision" in q for q in queries)

    def test_multiple_types(self):
        queries = generate_search_queries(
            topics=["ML"],
            opportunity_types=["PhD", "Internship"],
        )
        assert any("phd" in q.lower() for q in queries)
        assert any("intern" in q.lower() for q in queries)

    def test_respects_max_queries(self):
        queries = generate_search_queries(
            topics=["AI", "ML", "NLP"],
            opportunity_types=["PhD", "Internship", "Fellowship"],
            max_queries=10,
        )
        assert len(queries) <= 10

    def test_deduplicates(self):
        queries = generate_search_queries(
            topics=["NLP"],
            opportunity_types=["PhD"],
        )
        # All queries should be unique (case-insensitive)
        lower_queries = [q.lower() for q in queries]
        assert len(lower_queries) == len(set(lower_queries))

    def test_includes_site_searches(self):
        queries = generate_search_queries(
            topics=["Machine Learning"],
            opportunity_types=["PhD"],
            max_queries=50,
        )
        assert any("site:" in q for q in queries)

    def test_monitoring_queries(self):
        queries = generate_monitoring_queries(topics=["NLP", "CV"])
        assert len(queries) > 0
        assert any("NLP" in q for q in queries)
