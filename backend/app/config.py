import os
from dotenv import load_dotenv

load_dotenv()  # loads .env if present

# environment variables

class Settings:
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "company_llm")
    DB_USER: str = os.getenv("DB_USER", "company_llm_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "supersecretpassword")

    # Auth settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-secret-in-prod")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

settings = Settings()
