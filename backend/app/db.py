import psycopg2
from psycopg2.extras import RealDictCursor
from .config import settings

# connection helper for database

def get_connection():
    conn = psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        cursor_factory=RealDictCursor
    )
    return conn
