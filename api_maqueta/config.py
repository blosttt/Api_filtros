# config.py - VERSIÓN CORREGIDA
from pydantic_settings import BaseSettings
from typing import List, Optional
import secrets
from pydantic import ConfigDict, Field
import json


class Settings(BaseSettings):
    # Seguridad y Autenticación
    JWT_SECRET: str = "secreto123"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Agregar SECRET_KEY que tienes en .env
    SECRET_KEY: Optional[str] = None
    
    # Base de datos
    DATABASE_URL: str = "sqlite:///./productos.db"
    
    # CORS - usar validación para parsear el JSON
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Lista de orígenes permitidos para CORS"
    )
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 1000
    RATE_LIMIT_PER_HOUR: int = 10000
    
    # Headers de seguridad
    HSTS_ENABLED: bool = True
    CSP_ENABLED: bool = False
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Modo debug
    DEBUG: bool = True
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # Ignorar variables extra
        env_file_encoding="utf-8"
    )
    
    @classmethod
    def parse_cors_origins(cls, v):
        """Parsea CORS_ORIGINS si viene como string JSON"""
        if isinstance(v, str):
            try:
                # Intenta parsear como JSON
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                # Si falla, asume que es una string simple
                return [v.strip() for v in v.strip('[]').split(',')]
        return v


def generate_secret_key():
    """Genera una clave secreta segura para JWT"""
    return secrets.token_urlsafe(32)


# Configuración global
settings = Settings()

# Validar y ajustar CORS_ORIGINS
if isinstance(settings.CORS_ORIGINS, str):
    settings.CORS_ORIGINS = Settings.parse_cors_origins(settings.CORS_ORIGINS)

# Si no se configuró un secreto seguro, generar uno
if settings.JWT_SECRET == "password" or settings.JWT_SECRET == "secreto123":
    print("⚠️  ADVERTENCIA: Usando secreto inseguro. Generando uno temporal...")
    if settings.DEBUG:
        settings.JWT_SECRET = generate_secret_key()
        print(f"✅ Secreto JWT generado: {settings.JWT_SECRET[:10]}...")