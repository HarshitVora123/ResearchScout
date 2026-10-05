"""Skill extraction and taxonomy mapping."""

import re

from app.nlp.keyword_extraction import (
    ALL_SKILLS,
    PROGRAMMING_LANGUAGES,
    RESEARCH_AREAS,
)

# ── Skill Aliases (normalize variants to canonical form) ─
SKILL_ALIASES: dict[str, str] = {
    "py": "python",
    "python3": "python",
    "cpp": "c++",
    "c/c++": "c++",
    "node": "javascript",
    "nodejs": "javascript",
    "node.js": "javascript",
    "ts": "typescript",
    "golang": "go",
    "tf": "tensorflow",
    "torch": "pytorch",
    "sk-learn": "scikit-learn",
    "hf": "huggingface",
    "hugging face": "huggingface",
    "k8s": "kubernetes",
    "pg": "postgresql",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "es": "elasticsearch",
    "elastic search": "elasticsearch",
    "aws sagemaker": "aws",
    "gcloud": "gcp",
    "google cloud": "gcp",
    "microsoft azure": "azure",
    "openai": "openai api",
}

# ── Research Area Aliases ────────────────────────────
AREA_ALIASES: dict[str, str] = {
    "nlp": "natural language processing",
    "cv": "computer vision",
    "rl": "reinforcement learning",
    "ml": "machine learning",
    "dl": "deep learning",
    "llm": "large language models",
    "llms": "large language models",
    "gnn": "graph neural networks",
    "gnns": "graph neural networks",
    "xai": "explainable ai",
    "fl": "federated learning",
    "gen ai": "generative ai",
    "genai": "generative ai",
    "ir": "information retrieval",
    "recsys": "recommendation systems",
    "rec sys": "recommendation systems",
    "asr": "speech processing",
    "tts": "speech processing",
    "nlu": "natural language processing",
    "nlg": "natural language processing",
    "kg": "knowledge graphs",
    "kgs": "knowledge graphs",
    "mas": "multi-agent systems",
}


def extract_skills(text: str) -> list[str]:
    """
    Extract technical skills from text with alias normalization.

    Returns a deduplicated list of canonical skill names.
    """
    text_lower = text.lower()
    found: set[str] = set()

    # Check aliases first (maps variants to canonical names)
    for alias, canonical in SKILL_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", text_lower):
            found.add(canonical)

    # Check canonical skill names
    for skill in ALL_SKILLS:
        if re.search(rf"\b{re.escape(skill)}\b", text_lower):
            found.add(skill)

    return sorted(found)


def extract_programming_languages(text: str) -> list[str]:
    """Extract programming languages from text."""
    text_lower = text.lower()
    found: set[str] = set()

    # Special handling for c++ / c#
    if "c++" in text_lower or "cpp" in text_lower:
        found.add("c++")
    if "c#" in text_lower or "csharp" in text_lower:
        found.add("c#")

    for alias, canonical in SKILL_ALIASES.items():
        if canonical in PROGRAMMING_LANGUAGES and canonical not in found:
            if re.search(rf"(?:^|\W){re.escape(alias)}(?:$|\W)", text_lower):
                found.add(canonical)

    for lang in PROGRAMMING_LANGUAGES:
        if lang not in found:
            pattern = rf"\b{re.escape(lang)}\b" if lang.isalnum() else rf"(?:^|\W){re.escape(lang)}(?:$|\W)"
            if re.search(pattern, text_lower):
                found.add(lang)

    return sorted(found)


def extract_research_areas(text: str) -> list[str]:
    """Extract research areas from text with alias normalization."""
    text_lower = text.lower()
    found: set[str] = set()

    for alias, canonical in AREA_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", text_lower):
            found.add(canonical)

    for area in RESEARCH_AREAS:
        if area in text_lower:
            found.add(area)

    return sorted(found)


def compute_skill_overlap(
    required: list[str], user_skills: list[str]
) -> tuple[list[str], list[str], float]:
    """
    Compute skill overlap between opportunity requirements and user skills.

    Returns:
        (matched_skills, missing_skills, overlap_ratio)
    """
    # Normalize both lists
    required_normalized = {s.lower() for s in required}
    user_normalized = {s.lower() for s in user_skills}

    matched = sorted(required_normalized & user_normalized)
    missing = sorted(required_normalized - user_normalized)

    if not required_normalized:
        return matched, missing, 1.0

    overlap = len(matched) / len(required_normalized)
    return matched, missing, overlap
