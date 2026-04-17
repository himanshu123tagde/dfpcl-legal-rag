from __future__ import annotations

import re
from dataclasses import dataclass


_NON_WORD_RE = re.compile(r"[^a-z0-9]+")
_FIELD_KEYS = "doc_type|doctype|jurisdiction|court|language"
_FIELD_RE = re.compile(
    rf"\b(?P<key>{_FIELD_KEYS})\s*:\s*(?P<value>.+?)(?=(?:\b(?:{_FIELD_KEYS})\s*:)|$)",
    re.I,
)

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "be",
    "by",
    "can",
    "could",
    "do",
    "does",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "should",
    "the",
    "this",
    "to",
    "we",
    "what",
    "when",
    "where",
    "which",
    "who",
    "will",
    "with",
    "within",
    "without",
    "you",
    "your",
    "doc",
    "type",
    "doctype",
    "doc_type",
    "jurisdiction",
    "court",
    "language",
}


@dataclass(frozen=True)
class QueryAnalysis:
    keyword: str
    optimized_query_text: str
    needs_hyde: bool = False
    doc_type: str | None = None
    jurisdiction: str | None = None
    language: str | None = None


def _normalize(text: str) -> str:
    return _NON_WORD_RE.sub(" ", text.lower()).strip()


def _extract_fields(question: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for match in _FIELD_RE.finditer(question):
        key = match.group("key").strip().lower()
        value = match.group("value").strip().strip(",;.")
        if value:
            out[key] = value
    return out


def _detect_doc_type(normalized_question: str) -> str | None:
    # Check for 'judgment' first because legal queries often mention 'contract'
    # in the context of a judgment (e.g., "judgment regarding breach of contract").
    if any(w in normalized_question for w in ["judgment", "judgement", "order", "decree", "appeal"]):
        return "judgment"
    if any(w in normalized_question for w in ["contract", "agreement", "msa", "sow"]):
        return "contract"
    if any(w in normalized_question for w in ["regulation", "rule", "rules", "act", "notification", "circular"]):
        return "regulation"
    if any(w in normalized_question for w in ["email", "mail", "letter", "correspondence"]):
        return "correspondence"
    return None


def _choose_keyword(normalized_question: str) -> str:
    tokens = [t for t in normalized_question.split() if len(t) >= 3 and t not in _STOPWORDS]
    if not tokens:
        tokens = [t for t in normalized_question.split() if t]
    if not tokens:
        return "legal"

    # Cosmos Stage 1 uses CONTAINS(keyword), so one strong token works better than long phrases.
    # Prefer the longest token; use first occurrence as tie-breaker.
    best = max(tokens, key=lambda t: (len(t), -tokens.index(t)))
    return best


# ---------------------------------------------------------------------------
# HyDE gating heuristic
# ---------------------------------------------------------------------------
_HYDE_TRIGGER_PHRASES = {
    "what happens if",
    "what are the",
    "what is the",
    "what are our",
    "how does",
    "how can",
    "explain",
    "summarize",
    "summarise",
    "describe",
    "implications",
    "consequences",
    "liabilities",
    "legal effect",
    "rights and obligations",
    "under what circumstances",
    "what constitutes",
}

_NAVIGATIONAL_PREFIXES = {
    "find",
    "show",
    "get",
    "list",
    "fetch",
    "retrieve",
    "lookup",
    "look up",
    "pull up",
    "give me",
}


def _should_use_hyde(normalized_question: str) -> bool:
    """
    Decide whether HyDE should fire for this query.

    Trigger when the question is conceptual / analytical:
    - Contains a known conceptual trigger phrase, OR
    - Is longer than 6 content words (after stopword removal).

    Skip when the question looks navigational / direct:
    - Starts with a known navigational verb, OR
    - Is very short (≤ 4 content words).
    """
    # Quick skip: navigational prefixes
    for prefix in _NAVIGATIONAL_PREFIXES:
        if normalized_question.startswith(prefix):
            return False

    # Trigger phrases
    for phrase in _HYDE_TRIGGER_PHRASES:
        if phrase in normalized_question:
            return True

    # Length-based heuristic (content words only)
    content_words = [
        w for w in normalized_question.split()
        if len(w) >= 3 and w not in _STOPWORDS
    ]
    return len(content_words) > 6


def _normalize_jurisdiction(value: str) -> str:
    """
    POC heuristic:
    - Prefer a leading title-cased phrase (e.g. 'Bombay High Court')
    - Fall back to the first token (works for 'Delhi', 'Mumbai', etc.)
    """
    raw = value.strip().strip(",;.")
    if not raw:
        return raw

    tokens = raw.split()
    titled: list[str] = []
    for tok in tokens:
        cleaned = tok.strip(",;.")
        if cleaned and cleaned[0].isupper():
            titled.append(cleaned)
        else:
            break

    if titled:
        return " ".join(titled)
    return tokens[0].strip(",;.") if tokens else raw


def analyze_query(question: str) -> QueryAnalysis:
    normalized = _normalize(question)
    fields = _extract_fields(question)

    language = fields.get("language")
    jurisdiction = fields.get("jurisdiction") or fields.get("court")
    if jurisdiction:
        jurisdiction = _normalize_jurisdiction(jurisdiction)

    doc_type = fields.get("doc_type") or fields.get("doctype") or _detect_doc_type(normalized)

    keyword = _choose_keyword(normalized)
    optimized_query_text = question.strip()
    needs_hyde = _should_use_hyde(normalized)

    return QueryAnalysis(
        keyword=keyword,
        optimized_query_text=optimized_query_text,
        needs_hyde=needs_hyde,
        doc_type=doc_type,
        jurisdiction=jurisdiction,
        language=language,
    )
