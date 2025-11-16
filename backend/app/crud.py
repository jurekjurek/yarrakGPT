from typing import List
from uuid import UUID
from passlib.context import CryptContext
from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import RealDictCursor

# helper functions for the interaction with the database

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_tenant(conn: PGConnection, name: str) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO tenants (name)
            VALUES (%s)
            RETURNING id, name;
            """,
            (name,)
        )
        row = cur.fetchone()
        conn.commit()
        return row

def list_tenants(conn: PGConnection) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM tenants ORDER BY created_at;")
        rows = cur.fetchall()
        return rows

def create_user(conn: PGConnection, tenant_id: UUID, email: str, password: str, role: str) -> dict:
    password_hash = hash_password(password)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (tenant_id, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
            RETURNING id, tenant_id, email, role;
            """,
            (str(tenant_id), email, password_hash, role)
        )
        row = cur.fetchone()
        conn.commit()
        return row


def get_user_by_email_and_tenant(conn: PGConnection, tenant_id: UUID, email: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, tenant_id, email, password_hash, role
            FROM users
            WHERE tenant_id = %s AND email = %s
            """,
            (str(tenant_id), email),
        )
        row = cur.fetchone()
        return row


def get_user_by_id(conn: PGConnection, user_id: UUID) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, tenant_id, email, role
            FROM users
            WHERE id = %s
            """,
            (str(user_id),),
        )
        row = cur.fetchone()
        return row