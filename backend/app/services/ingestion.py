# backend/app/services/ingestion.py

from uuid import UUID
from typing import List
from psycopg2.extensions import connection as PGConnection
import os
from .chunking import read_pdf_text_by_page, chunk_text
from psycopg2.extras import Json

EMBEDDING_DIM = 768  # still needed for the embedding column; dummy for now


def dummy_embedding(text: str) -> list[float]:
    """
    Temporary placeholder for embedding generation.
    Right now, just returns a zero vector.
    Later: replace with a call to Vertex AI embeddings.
    """
    return [0.0] * EMBEDDING_DIM


def ingest_document(
    conn: PGConnection,
    tenant_id: UUID,
    document_id: UUID,
    file_path: str,
):
    """
    Ingest a single document:
    - read PDF by page
    - chunk each page using token-based chunking
    - insert chunks into DB with dummy embeddings and metadata (filename, page)
    - set documents.status = 'ready'
    """
    filename = os.path.basename(file_path)

    # 1. Read pages
    pages = read_pdf_text_by_page(file_path)

    # 2. Build chunks with metadata
    with conn.cursor() as cur:
        chunk_counter = 0
        for page_idx, page_text in enumerate(pages, start=1):
            if not page_text or not page_text.strip():
                continue
            chunks = chunk_text(page_text, max_tokens=220, overlap=40)
            for chunk_text_str in chunks:
                emb = dummy_embedding(chunk_text_str)
                metadata = {
                    "filename": filename,
                    "page": page_idx,
                }
                cur.execute(
                    """
                    INSERT INTO chunks (tenant_id, document_id, chunk_index, text, embedding, metadata)
                    VALUES (%s, %s, %s, %s, %s::vector, %s)
                    """,
                    (
                        str(tenant_id),
                        str(document_id),
                        chunk_counter,
                        chunk_text_str,
                        emb,
                        Json(metadata),
                    ),
                )
                chunk_counter += 1

        # 3. Update document status
        cur.execute(
            """
            UPDATE documents
            SET status = 'ready'
            WHERE id = %s
            """,
            (str(document_id),),
        )

    conn.commit()
