# backend/app/services/ingestion.py
from uuid import UUID
from typing import List
import numpy as np
from psycopg2.extensions import connection as PGConnection

from .chunking import extract_text_from_pdf, chunk_text

# this file: 
# extracts text 
# chunks it 
# inserts into 'chunks'
# updates the documents.status

EMBEDDING_DIM = 768  # adjust later to match Vertex AI embedding size

# this will be embedding AI in the future
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
    End-to-end ingestion for a single document:
    - extract text from file
    - chunk text
    - generate embeddings (dummy for now)
    - insert into chunks table
    - set documents.status = 'ready'
    """
    # 1. Extract text
    text = extract_text_from_pdf(file_path)

    # 2. Chunk text
    chunks = chunk_text(text)

    # 3. Insert chunks with dummy embeddings
    with conn.cursor() as cur:
        for idx, chunk in enumerate(chunks):
            emb = dummy_embedding(chunk)
            # note: CAST to vector via array::vector
            cur.execute(
                """
                INSERT INTO chunks (tenant_id, document_id, chunk_index, text, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s::vector, %s)
                """,
                (
                    str(tenant_id),
                    str(document_id),
                    idx,
                    chunk,
                    emb,  # psycopg2 will send as array, then we cast to vector
                    None,
                ),
            )

        # 4. Update document status
        cur.execute(
            """
            UPDATE documents
            SET status = 'ready'
            WHERE id = %s
            """,
            (str(document_id),),
        )

    conn.commit()
