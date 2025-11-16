# backend/app/main.py
from typing import List
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status
from uuid import UUID
import os

from .db import get_connection
from . import crud, schemas
from .services.ingestion import ingest_document
from .services import rag  # <-- NEW
from .services.auth import authenticate_user, create_access_token, get_current_user
from datetime import timedelta
from fastapi.middleware.cors import CORSMiddleware

from .schemas import UserOut
from .config import settings

DOCUMENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "documents")
os.makedirs(DOCUMENTS_DIR, exist_ok=True)


# contains the actual fast api app

app = FastAPI(title="Company LLM Backend")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/tenants", response_model=schemas.TenantOut)
def create_tenant(tenant: schemas.TenantCreate, conn=Depends(get_db)):
    row = crud.create_tenant(conn, tenant.name)
    return row

@app.get("/tenants", response_model=List[schemas.TenantOut])
def list_tenants(conn=Depends(get_db)):
    rows = crud.list_tenants(conn)
    return rows

@app.post("/users", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, conn=Depends(get_db)):
    try:
        row = crud.create_user(conn, user.tenant_id, user.email, user.password, user.role)
        return row
    except Exception as e:
        # minimal error handling for now
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: schemas.UserOut = Depends(get_current_user),
    conn = Depends(get_db),
):
    """
    Upload a document for a given tenant.

    - Saves the file to local storage
    - Inserts a row into documents
    - Runs ingestion (extract + chunk + dummy embeddings)
    """
    # get tenant id from current user
    tenant_id = current_user.tenant_id

    # Basic validation
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # 1. Save file to disk
    # document_id will be known after insert; for now we use a temp name
    original_filename = file.filename
    # use a temp path; we'll rename once document_id is known
    temp_path = os.path.join(DOCUMENTS_DIR, f"temp_{original_filename}")
    with open(temp_path, "wb") as f_out:
        content = await file.read()
        f_out.write(content)

    # 2. Create document row
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (tenant_id, title, original_filename, storage_path, status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                str(tenant_id),
                original_filename,  # title = original filename for now
                original_filename,
                "",  # temporary placeholder for storage_path, we'll update
                "uploaded",
            ),
        )
        row = cur.fetchone()
        document_id = row["id"]

        # Now that we know the document_id, compute final storage path
        final_filename = f"{document_id}_{original_filename}"
        final_path = os.path.join(DOCUMENTS_DIR, final_filename)

        # Rename temp file to final path
        os.rename(temp_path, final_path)

        # Update storage_path in DB
        cur.execute(
            """
            UPDATE documents
            SET storage_path = %s
            WHERE id = %s
            """,
            (final_path, str(document_id)),
        )

    conn.commit()

    # 3. Ingest document (sync for now)
    try:
        ingest_document(conn, tenant_id, document_id, final_path)
    except Exception as e:
        # If ingestion fails, mark document as error
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE documents
                SET status = 'error'
                WHERE id = %s
                """,
                (str(document_id),),
            )
        conn.commit()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")

    return {
        "document_id": document_id,
        "tenant_id": tenant_id,
        "filename": original_filename,
        "status": "ready",
    }


@app.post("/query", response_model=schemas.QueryResponse)
def query_data(
    payload: schemas.QueryRequest,
    current_user: schemas.UserOut = Depends(get_current_user),
    conn = Depends(get_db),
):
    """
    Ask a question about a tenant's documents.

    Steps:
    - embed the question (dummy for now)
    - retrieve top_k relevant chunks from DB
    - build a RAG prompt
    - call LLM (dummy for now)
    - return answer + sources
    """
    tenant_id = current_user.tenant_id
    question = payload.question
    top_k = payload.top_k

    # 1. Embed the question
    query_embedding = rag.get_query_embedding(question)

    # 2. Retrieve relevant chunks
    chunks = rag.retrieve_relevant_chunks(conn, tenant_id, query_embedding, top_k=top_k)

    if not chunks:
        # No chunks found for this tenant
        return schemas.QueryResponse(
            answer="Ich konnte keine passenden Informationen in den Dokumenten finden.",
            sources=[],
        )

    # 3. Build prompt
    prompt = rag.build_rag_prompt(question, chunks)

    # 4. Call LLM (dummy)
    answer = rag.call_llm(prompt)

    # 5. Build sources list
    sources = [
        schemas.SourceChunk(
            document_id=row["document_id"],
            chunk_index=row["chunk_index"],
            text=row["text"],
        )
        for row in chunks
    ]

    return schemas.QueryResponse(
        answer=answer,
        sources=sources,
    )


@app.post("/auth/login", response_model=schemas.Token)
def login(payload: schemas.UserLogin):
    """
    Login endpoint.

    Expects: tenant_id, email, password.
    Returns: JWT access token if credentials are valid.
    """
    user = authenticate_user(payload.tenant_id, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect tenant, email, or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user["id"]),
            "tenant_id": str(user["tenant_id"]),
            "email": user["email"],
            "role": user["role"],
        },
        expires_delta=access_token_expires,
    )
    return schemas.Token(access_token=access_token, token_type="bearer")

