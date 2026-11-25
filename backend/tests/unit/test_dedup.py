"""Unit tests for the Dedup Agent — MinHash and semantic deduplication."""

from app.agents.intelligence.dedup_agent import (
    DedupAgent,
    _minhash_signature,
    _tokenize,
    minhash_similarity,
)


class TestTokenize:
    """Test text tokenization for MinHash."""

    def test_basic_tokenization(self):
        tokens = _tokenize("PhD Position in Natural Language Processing")
        assert len(tokens) > 0
        # Should include word shingles and individual words
        assert "natural" in tokens or "processing" in tokens

    def test_empty_string(self):
        tokens = _tokenize("")
        assert len(tokens) == 0

    def test_removes_punctuation(self):
        tokens = _tokenize("Hello, World! (2025)")
        # Punctuation should be stripped
        for token in tokens:
            assert "!" not in token
            assert "," not in token

    def test_case_insensitive(self):
        tokens_upper = _tokenize("NLP Research Position")
        tokens_lower = _tokenize("nlp research position")
        assert tokens_upper == tokens_lower


class TestMinHash:
    """Test MinHash signature generation and comparison."""

    def test_identical_texts_match(self):
        text = "PhD Position in Natural Language Processing at MIT"
        sig_a = _minhash_signature(_tokenize(text))
        sig_b = _minhash_signature(_tokenize(text))
        sim = minhash_similarity(sig_a, sig_b)
        assert sim == 1.0

    def test_similar_texts_high_similarity(self):
        sig_a = _minhash_signature(_tokenize("PhD Position in Natural Language Processing"))
        sig_b = _minhash_signature(_tokenize("PhD Position in NLP and Natural Language Processing"))
        sim = minhash_similarity(sig_a, sig_b)
        assert sim > 0.5

    def test_different_texts_low_similarity(self):
        sig_a = _minhash_signature(_tokenize("PhD Position in Natural Language Processing"))
        sig_b = _minhash_signature(_tokenize("Postdoc in Quantum Computing and Physics"))
        sim = minhash_similarity(sig_a, sig_b)
        assert sim < 0.4

    def test_empty_shingles(self):
        sig = _minhash_signature(set())
        assert len(sig) == 128
        assert all(s == 0 for s in sig)


class TestDedupAgent:
    """Test the DedupAgent's MinHash index."""

    def test_add_and_find_duplicate(self):
        agent = DedupAgent()
        agent.add_to_index("opp-1", "PhD in NLP", "MIT")

        result = agent.check_minhash("PhD in NLP", "MIT")
        assert result.is_duplicate is True
        assert result.duplicate_id == "opp-1"
        assert result.match_type == "minhash"
        assert result.similarity_score >= 0.8

    def test_similar_title_detected(self):
        agent = DedupAgent()
        agent.add_to_index(
            "opp-1",
            "PhD Position in Natural Language Processing",
            "MIT",
        )

        result = agent.check_minhash(
            "PhD Position in NLP and Natural Language Processing",
            "MIT",
        )
        assert result.is_duplicate is True

    def test_different_opportunity_not_flagged(self):
        agent = DedupAgent()
        agent.add_to_index("opp-1", "PhD in NLP", "MIT")

        result = agent.check_minhash(
            "Postdoc in Quantum Computing",
            "Stanford",
        )
        assert result.is_duplicate is False

    def test_index_size(self):
        agent = DedupAgent()
        assert agent.index_size == 0
        agent.add_to_index("a", "Title A", "Org A")
        agent.add_to_index("b", "Title B", "Org B")
        assert agent.index_size == 2

    def test_multiple_entries_best_match(self):
        agent = DedupAgent()
        agent.add_to_index("opp-1", "PhD in Natural Language Processing", "MIT")
        agent.add_to_index("opp-2", "Research Intern in Computer Vision", "Google")
        agent.add_to_index("opp-3", "PhD in Natural Language Processing and Language Models", "MIT")

        # Should match opp-1 or opp-3 (both NLP at MIT)
        result = agent.check_minhash("PhD in Natural Language Processing", "MIT")
        assert result.is_duplicate is True
        assert result.duplicate_id in ("opp-1", "opp-3")
