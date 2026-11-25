"""Unit tests for the Embedding Agent — text composition and caching."""

from app.agents.intelligence.embedding_agent import EmbeddingAgent


class TestEmbeddingComposition:
    """Test text composition for embedding generation."""

    def setup_method(self):
        self.agent = EmbeddingAgent()

    def test_compose_opportunity_full(self):
        text = self.agent.compose_opportunity_text(
            {
                "title": "PhD in NLP",
                "organization": "MIT",
                "opportunity_type": "PhD",
                "department": "CSAIL",
                "country": "USA",
                "city": "Cambridge",
                "research_areas": ["NLP", "Machine Learning"],
                "required_skills": ["Python", "PyTorch"],
                "programming_languages": ["Python", "C++"],
                "funding_type": "Fully Funded",
                "summary": "Work on large language models.",
            }
        )
        assert "PhD in NLP" in text
        assert "MIT" in text
        assert "NLP" in text
        assert "Python" in text
        assert "Cambridge, USA" in text

    def test_compose_opportunity_minimal(self):
        text = self.agent.compose_opportunity_text(
            {
                "title": "Research Position",
            }
        )
        assert "Research Position" in text
        assert len(text) > 0

    def test_compose_opportunity_empty(self):
        text = self.agent.compose_opportunity_text({})
        assert text == ""

    def test_compose_user_full(self):
        text = self.agent.compose_user_text(
            {
                "full_name": "Jane Smith",
                "degree_level": "PhD",
                "university": "Stanford",
                "career_goals": "AI researcher",
                "skills": [{"skill_name": "Python"}, {"skill_name": "PyTorch"}],
                "research_interests": [{"topic": "NLP"}, {"topic": "ML"}],
                "publications": [{"title": "LLM Survey"}],
                "preferred_countries": ["USA", "UK"],
            }
        )
        assert "Jane Smith" in text
        assert "Stanford" in text
        assert "Python" in text
        assert "NLP" in text
        assert "LLM Survey" in text

    def test_compose_user_minimal(self):
        text = self.agent.compose_user_text({"full_name": "John Doe"})
        assert "John Doe" in text

    def test_compose_user_with_string_skills(self):
        """Test that string skills (not dicts) are handled."""
        text = self.agent.compose_user_text(
            {
                "skills": ["Python", "TensorFlow"],
            }
        )
        assert "Python" in text
        assert "TensorFlow" in text


class TestEmbeddingCache:
    """Test the embedding cache behavior."""

    def test_cache_key_consistency(self):
        from app.agents.intelligence.embedding_agent import _cache_key

        key1 = _cache_key("hello world")
        key2 = _cache_key("hello world")
        assert key1 == key2

    def test_cache_key_differs(self):
        from app.agents.intelligence.embedding_agent import _cache_key

        key1 = _cache_key("hello")
        key2 = _cache_key("world")
        assert key1 != key2
