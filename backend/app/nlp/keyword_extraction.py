"""NLP keyword extraction using KeyBERT and regex patterns."""

import re
from dataclasses import dataclass, field

# ── Predefined Skill Taxonomy ────────────────────────
PROGRAMMING_LANGUAGES = {
    "python", "java", "c++", "c", "r", "matlab", "julia", "scala",
    "javascript", "typescript", "rust", "go", "kotlin", "swift",
    "sql", "bash", "shell", "perl", "ruby", "php", "haskell",
    "lisp", "prolog", "fortran", "assembly", "verilog", "vhdl",
}

ML_FRAMEWORKS = {
    "pytorch", "tensorflow", "keras", "jax", "flax", "scikit-learn",
    "sklearn", "xgboost", "lightgbm", "catboost", "huggingface",
    "transformers", "spacy", "nltk", "gensim", "opencv", "detectron2",
    "mmdetection", "paddlepaddle", "mxnet", "caffe", "onnx",
    "langchain", "langgraph", "llamaindex", "openai api",
}

RESEARCH_TOOLS = {
    "docker", "kubernetes", "git", "linux", "aws", "gcp", "azure",
    "spark", "hadoop", "kafka", "airflow", "mlflow", "wandb",
    "ray", "dask", "postgresql", "mongodb", "neo4j", "redis",
    "elasticsearch", "grafana", "prometheus", "terraform", "ansible",
    "latex", "overleaf", "jupyter", "colab",
}

RESEARCH_AREAS = {
    "natural language processing", "nlp", "computer vision", "cv",
    "machine learning", "deep learning", "reinforcement learning",
    "robotics", "ai safety", "ai alignment", "generative ai",
    "large language models", "llm", "knowledge graphs",
    "information retrieval", "recommendation systems",
    "speech processing", "audio processing", "signal processing",
    "bioinformatics", "computational biology", "drug discovery",
    "climate science", "quantum computing", "quantum machine learning",
    "autonomous driving", "medical imaging", "healthcare ai",
    "graph neural networks", "federated learning", "privacy",
    "fairness", "explainable ai", "xai", "interpretability",
    "multi-agent systems", "multimodal learning",
    "transfer learning", "meta-learning", "few-shot learning",
    "continual learning", "self-supervised learning",
    "contrastive learning", "diffusion models", "gan",
    "variational autoencoders", "bayesian methods",
    "optimization", "convex optimization", "causal inference",
    "time series", "anomaly detection", "data mining",
}

ALL_SKILLS = PROGRAMMING_LANGUAGES | ML_FRAMEWORKS | RESEARCH_TOOLS


@dataclass
class NLPResult:
    """Result of NLP analysis on opportunity text."""

    keywords: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    programming_languages: list[str] = field(default_factory=list)
    research_areas: list[str] = field(default_factory=list)
    deadline_str: str | None = None
    is_opportunity: bool = False
    opportunity_type_hint: str | None = None


# ── Opportunity Detection Patterns ───────────────────
OPPORTUNITY_PATTERNS = [
    r"(?i)\b(?:phd|ph\.d)\b.*(?:position|student|opening|candidate|vacancy)",
    r"(?i)\bresearch\s+(?:intern|internship|assistant|associate|fellow)\b",
    r"(?i)\b(?:postdoc|post-doc|postdoctoral)\b.*(?:position|fellow|researcher)",
    r"(?i)\bfellowship\b",
    r"(?i)\bscholarship\b",
    r"(?i)\bsummer\s+(?:school|program|research|internship)\b",
    r"(?i)\b(?:ai|ml)\s+residen(?:cy|t)\b",
    r"(?i)\bmaster(?:'s)?\s+thesis\b",
    r"(?i)\bundergraduate\s+research\b",
    r"(?i)\bopen\s+position\b",
    r"(?i)\bwe\s+are\s+(?:looking|hiring|seeking)\b",
    r"(?i)\bapply\s+(?:now|here|by|before)\b",
    r"(?i)\bdeadline\s*(?::|is|for)\b",
    r"(?i)\bfully\s+funded\b",
    r"(?i)\bstipend\b",
]

OPPORTUNITY_TYPE_PATTERNS = {
    "PhD": [r"(?i)\b(?:phd|ph\.d|doctoral)\b"],
    "Postdoc": [r"(?i)\b(?:postdoc|post-doc|postdoctoral)\b"],
    "Internship": [r"(?i)\b(?:intern|internship)\b"],
    "Research Assistant": [r"(?i)\bresearch\s+assistant\b"],
    "Fellowship": [r"(?i)\bfellowship\b"],
    "Scholarship": [r"(?i)\bscholarship\b"],
    "Summer School": [r"(?i)\bsummer\s+(?:school|program)\b"],
    "AI Residency": [r"(?i)\b(?:ai|ml)\s+residen(?:cy|t)\b"],
    "Masters Thesis": [r"(?i)\bmaster(?:'s)?\s+thesis\b"],
    "Undergraduate Research": [r"(?i)\bundergraduate\s+research\b"],
}


def analyze_text(text: str) -> NLPResult:
    """
    Run the full NLP pipeline on opportunity text.

    This is a fast, rule-based pipeline that doesn't require
    any ML models to load. Used as a pre-filter before LLM extraction.
    """
    text_lower = text.lower()
    result = NLPResult()

    # 1. Check if this is likely an opportunity page
    match_count = sum(
        1 for pattern in OPPORTUNITY_PATTERNS if re.search(pattern, text)
    )
    result.is_opportunity = match_count >= 2

    # 2. Detect opportunity type
    for opp_type, patterns in OPPORTUNITY_TYPE_PATTERNS.items():
        if any(re.search(p, text) for p in patterns):
            result.opportunity_type_hint = opp_type
            break

    # 3. Extract programming languages
    from app.nlp.skill_extraction import extract_programming_languages
    result.programming_languages = extract_programming_languages(text)

    # 4. Extract skills (frameworks + tools)
    result.skills = [
        skill for skill in (ML_FRAMEWORKS | RESEARCH_TOOLS)
        if re.search(rf"\b{re.escape(skill)}\b", text_lower)
    ]

    # 5. Extract research areas
    result.research_areas = [
        area for area in RESEARCH_AREAS
        if area in text_lower
    ]

    # 6. Extract keywords (top nouns/phrases via simple frequency)
    result.keywords = _extract_keywords_simple(text)

    # 7. Extract deadline string
    result.deadline_str = _extract_deadline_string(text)

    return result


def _extract_keywords_simple(text: str, top_k: int = 10) -> list[str]:
    """Extract keywords using simple word frequency (no ML required)."""
    # Remove common HTML artifacts and short words
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())

    # Filter stopwords (minimal set)
    stopwords = {
        "that", "this", "with", "from", "have", "will", "been",
        "they", "their", "there", "were", "what", "when", "where",
        "which", "would", "could", "should", "about", "more",
        "also", "some", "than", "other", "into", "only", "very",
        "just", "most", "such", "each", "both", "does", "being",
        "your", "please", "university", "research", "contact",
        "email", "application", "information", "http", "https",
        "page", "click", "here", "home", "menu", "navigation",
    }
    filtered = [w for w in words if w not in stopwords]

    # Count frequency
    freq: dict[str, int] = {}
    for word in filtered:
        freq[word] = freq.get(word, 0) + 1

    # Return top-k by frequency
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_words[:top_k]]


def _extract_deadline_string(text: str) -> str | None:
    """Extract deadline date string from text using regex patterns."""
    # Common deadline patterns
    patterns = [
        # "Deadline: January 15, 2025"
        r"(?i)deadline[:\s]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})",
        # "Apply by March 1, 2025"
        r"(?i)apply\s+(?:by|before)[:\s]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})",
        # "Deadline: 15/01/2025" or "Deadline: 2025-01-15"
        r"(?i)deadline[:\s]+(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})",
        r"(?i)deadline[:\s]+(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})",
        # "Due date: Jan 15, 2025"
        r"(?i)due\s+date[:\s]+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})",
        # "Applications close on February 28, 2025"
        r"(?i)close[sd]?\s+(?:on\s+)?([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()

    return None
