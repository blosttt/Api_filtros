from pydantic_settings import BaseSettings


class Settings:
    JWT_SECRET: str = "secreto123"
    JWT_ALGORITHM: str = "HS256"
    DATABASE_URL: str = "sqlite:///./productos.db"

settings = Settings()