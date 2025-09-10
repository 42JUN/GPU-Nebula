import os

class Settings:
    PROJECT_NAME: str = "GPU-Nebula"
    PROJECT_VERSION: str = "0.1.0"

    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/gpu_nebula_db")
    # For local development, you might use:
    # DATABASE_URL: str = "postgresql://user:password@localhost:5432/gpu_nebula_db"

settings = Settings()
