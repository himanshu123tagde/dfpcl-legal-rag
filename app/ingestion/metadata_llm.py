from __future__ import annotations

import re
from collections import Counter

from app.utils.text_utils import normalize_whitespace

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")
_STOPWORDS = {
    "about",
    "above",
    "after",
    "again",
    "all",
    "also",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "below",
    "between",
    "both",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "doing",
    "down",
    "during",
    "each",
    "few",
    "for",
    "from",
    "further",
    "had",
    "has",
    "have",
    "having",
    "he",
    "her",
    "here",
    "hers",
    "herself",
    "him",
    "himself",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "itself",
    "just",
    "may",
    "me",
    "more",
    "most",
    "my",
    "myself",
    "no",
    "nor",
    "not",
    "now",
    "of",
    "off",
    "on",
    "once",
    "only",
    "or",
    "other",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "own",
    "same",
    "she",
    "should",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "to",
    "too",
    "under",
    "until",
    "up",
    "very",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "why",
    "will",
    "with",
    "you",
    "your",
    "yours",
    "yourself",
    "yourselves",
}


def extract_keywords(text: str, *, max_keywords: int = 12) -> list[str]:
    """
    Phase 6 POC keywording:
    - purely heuristic (no LLM)
    - used to make Cosmos Stage 1 narrowing useful
    """
    tokens = [t.lower() for t in _TOKEN_RE.findall(text)]
    tokens = [t for t in tokens if t not in _STOPWORDS]
    if not tokens:
        return []
    counts = Counter(tokens)
    return [w for w, _ in counts.most_common(max_keywords)]


def build_naive_summary(text: str, *, max_chars: int = 1200) -> str:
    """
    Phase 6 POC summary:
    - not an LLM summary
    - good enough to populate Cosmos for Stage 1 and context enrichment
    """
    normalized = normalize_whitespace(text)
    if not normalized:
        return ""
    return normalized[:max_chars]
