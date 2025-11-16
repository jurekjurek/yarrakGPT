# backend/app/services/rag.py
from typing import List
from uuid import UUID
from psycopg2.extensions import connection as PGConnection

from .ingestion import EMBEDDING_DIM, dummy_embedding  # reuse for now


def get_query_embedding(question: str) -> list[float]:
    """
    For now, reuse the dummy embedding.
    Later: replace with real Vertex AI embeddings.
    """
    return dummy_embedding(question)


def retrieve_relevant_chunks(
    conn: PGConnection,
    tenant_id: UUID,
    query_embedding: list[float],
    top_k: int = 5,
) -> List[dict]:
    """
    Retrieve top_k chunks for a given tenant using vector similarity.
    Returns a list of dicts: {document_id, chunk_index, text}
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT document_id, chunk_index, text
            FROM chunks
            WHERE tenant_id = %s
            ORDER BY embedding <-> %s::vector
            LIMIT %s;
            """,
            (str(tenant_id), query_embedding, top_k),
        )
        rows = cur.fetchall()
        # rows is a list of RealDictRow → behaves like dicts
        return rows


def build_rag_prompt(question: str, chunks: List[dict]) -> str:
    """
    Build a simple RAG prompt from the question and retrieved chunks.
    Later you can replace this with your more advanced prompt logic.
    """
    context_parts = []
    for i, ch in enumerate(chunks, start=1):
        context_parts.append(f"[{i}] {ch['text']}\n")

    context_text = "\n".join(context_parts)

    prompt = f"""Du bist ein hilfreicher Assistent für Vertrags- und Kundendaten in deutscher Sprache.
Du beantwortest Fragen ausschließlich auf Basis des bereitgestellten Kontextes.
Wenn die Antwort nicht im Kontext enthalten ist, sag ehrlich, dass du es nicht weißt.

Kontext:
{context_text}

Frage:
{question}

Antwort (auf Deutsch):
"""
    return prompt


def call_llm(prompt: str) -> str:
    """
    Dummy LLM call.

    For now, just returns the prompt itself with a placeholder answer.
    Later: replace this with a real call to Vertex AI (Gemini).
    """
    # TODO: implement real LLM call
    # For now, we fake an answer:
    return (
        "DUMMY_ANSWER: (Hier würde die LLM-Antwort stehen.)\n\n"
        "Prompt, das an das LLM geschickt worden wäre:\n\n"
        + prompt
    )
