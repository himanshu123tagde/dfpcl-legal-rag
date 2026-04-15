from __future__ import annotations

LEGAL_RAG_SYSTEM_PROMPT = (
    "You are a legal research assistant. "
    "Answer only from the provided context. "
    "Do not invent facts, clauses, parties, dates, or legal conclusions that are not supported by the context. "
    "If the context is insufficient, say that clearly and state what is missing. "
    "Keep the answer concise, precise, and useful for an internal legal user."
)


def build_grounded_user_prompt(*, question: str, context: str) -> str:
    return (
        "Use only the retrieved legal context below to answer the user's question.\n\n"
        "If the answer is only partial, say that it is partial.\n"
        "If the context does not support an answer, say that there is not enough indexed context.\n\n"
        f"Question:\n{question}\n\n"
        f"Retrieved context:\n{context}"
    )
