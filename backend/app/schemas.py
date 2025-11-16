from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta

# pydantic models for request / response bodies

class TenantCreate(BaseModel):
    name: str

class TenantOut(BaseModel):
    id: UUID
    name: str

class UserCreate(BaseModel):
    tenant_id: UUID
    email: EmailStr
    password: str
    role: str = "user"

class UserOut(BaseModel):
    id: UUID
    tenant_id: UUID
    email: EmailStr
    role: str

from typing import List

class QueryRequest(BaseModel):
    question: str
    top_k: int = 5  # how many chunks to retrieve

class SourceChunk(BaseModel):
    document_id: UUID
    chunk_index: int
    text: str

class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]

# for authentification
class UserLogin(BaseModel):
    tenant_id: UUID
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: UUID
    tenant_id: UUID
    email: EmailStr
    role: str