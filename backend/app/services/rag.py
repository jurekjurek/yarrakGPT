# backend/app/services/rag.py

from typing import List, Dict, Any
from uuid import UUID
from psycopg2.extensions import connection as PGConnection

from .chunking import (
    simple_normalize,
    rewrite_query,
    hybrid_search,
    build_prompt as build_prompt_from_chunks,
)


def build_corpus_from_db_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a corpus dict from DB rows in chunks:
    - records: list of {idx, document_id, chunk_index, filename, page, text}
    - doc_tokens: list of token lists for each record
    """
    records: List[Dict[str, Any]] = []
    doc_tokens: List[List[str]] = []

    for idx, row in enumerate(rows):
        text = row["text"] or ""
        tokens = simple_normalize(text)
        meta = row.get("metadata") or {}
        filename = meta.get("filename", str(row["document_id"]))
        page = meta.get("page", "?")

        records.append(
            {
                "idx": idx,
                "document_id": row["document_id"],
                "chunk_index": row["chunk_index"],
                "filename": filename,
                "page": page,
                "text": text,
            }
        )
        doc_tokens.append(tokens)

    return {"records": records, "doc_tokens": doc_tokens}


def retrieve_relevant_chunks_lexical(
    conn: PGConnection,
    tenant_id: UUID,
    question: str,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Lexical retrieval using BM25 + TF-IDF hybrid for all chunks of a tenant.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT document_id, chunk_index, text, metadata
            FROM chunks
            WHERE tenant_id = %s
            """,
            (str(tenant_id),),
        )
        rows = cur.fetchall()

    if not rows:
        return []

    corpus = build_corpus_from_db_rows(rows)
    qobj = rewrite_query(question)
    hits = hybrid_search(qobj, corpus, top_k=top_k)
    return hits


def build_rag_prompt(question: str, hits: List[Dict[str, Any]]) -> str:
    """
    Build the full prompt from question and hits, using your existing logic.
    """
    return build_prompt_from_chunks(question, hits)


def call_llm(prompt: str) -> str:
    """
    Dummy LLM call.
    Later: replace with real Vertex AI call.
    """
    return (
        "DUMMY_ANSWER: (Hier würde die LLM-Antwort stehen.)\n\n"
        "Prompt, das an das LLM geschickt worden wäre:\n\n"
        + prompt
    )
