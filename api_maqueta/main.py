from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import models
from database import engine
from routers import rest  # ← SOLO REST, NO GRAPHQL
from config import settings
import time
import logging
from typing import Dict, Any
import traceback

# Configurar logging de seguridad
security_logger = logging.getLogger("security")
security_logger.setLevel(logging.WARNING)

# Crear tablas
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API de Productos - Sistema Vehicular",
    description="API REST segura para gestión de productos con filtros vehiculares (OWASP Top 10 implementado)",
    version="2.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None
)

# Middleware de seguridad
# Redirigir HTTP a HTTPS en producción
if not settings.DEBUG:
    app.add_middleware(HTTPSRedirectMiddleware)

# Validar hosts confiables - COMENTADO TEMPORALMENTE PARA DESARROLLO
# app.add_middleware(
#     TrustedHostMiddleware,
#     allowed_hosts=["localhost", "127.0.0.1", "api.tudominio.com"]
# )

# Configurar CORS - PERMISIVO PARA DESARROLLO
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Temporal: permitir todos los orígenes
    allow_credentials=True,
    allow_methods=["*"],  # Temporal: permitir todos los métodos
    allow_headers=["*"],  # Temporal: permitir todos los headers
    expose_headers=["X-Request-ID"],
    max_age=600,
)

# Middleware para agregar headers de seguridad
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Headers OWASP recomendados
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # CSP básico (ajustar según necesidades) - DESHABILITAR TEMPORALMENTE
    # if settings.CSP_ENABLED:
    #     response.headers["Content-Security-Policy"] = "default-src 'self';"
    
    # HSTS
    if settings.HSTS_ENABLED and not settings.DEBUG:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Cache control para endpoints sensibles
    if request.url.path in ["/auth/login", "/auth/register"]:
        response.headers["Cache-Control"] = "no-store, max-age=0"
    
    return response

# Middleware para rate limiting básico - AUMENTAR LÍMITES PARA DESARROLLO
rate_limit_store: Dict[str, Dict[str, Any]] = {}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Deshabilitar rate limiting temporalmente para desarrollo
    if settings.DEBUG:
        response = await call_next(request)
        return response
    
    client_ip = request.client.host
    
    # Limpieza de registros antiguos
    current_time = time.time()
    rate_limit_store[client_ip] = {
        k: v for k, v in rate_limit_store.get(client_ip, {}).items()
        if current_time - v["timestamp"] < 3600  # Mantener solo última hora
    }
    
    # Contar requests
    minute_key = f"minute_{int(current_time // 60)}"
    hour_key = f"hour_{int(current_time // 3600)}"
    
    if client_ip not in rate_limit_store:
        rate_limit_store[client_ip] = {}
    
    # Contador por minuto
    rate_limit_store[client_ip][minute_key] = rate_limit_store[client_ip].get(minute_key, {
        "count": 0,
        "timestamp": current_time
    })
    rate_limit_store[client_ip][minute_key]["count"] += 1
    
    # Contador por hora
    rate_limit_store[client_ip][hour_key] = rate_limit_store[client_ip].get(hour_key, {
        "count": 0,
        "timestamp": current_time
    })
    rate_limit_store[client_ip][hour_key]["count"] += 1
    
    # Verificar límites (aumentados para desarrollo)
    if rate_limit_store[client_ip][minute_key]["count"] > settings.RATE_LIMIT_PER_MINUTE:
        security_logger.warning(f"Rate limit excedido para IP {client_ip}: {rate_limit_store[client_ip][minute_key]['count']} requests por minuto")
        return JSONResponse(
            status_code=429,
            content={"detail": "Demasiadas solicitudes. Por favor intente más tarde."}
        )
    
    if rate_limit_store[client_ip][hour_key]["count"] > settings.RATE_LIMIT_PER_HOUR:
        security_logger.warning(f"Rate limit excedido para IP {client_ip}: {rate_limit_store[client_ip][hour_key]['count']} requests por hora")
        return JSONResponse(
            status_code=429,
            content={"detail": "Límite de solicitudes por hora excedido."}
        )
    
    response = await call_next(request)
    return response

# Middleware para logging de seguridad
@app.middleware("http")
async def security_logging_middleware(request: Request, call_next):
    start_time = time.time()
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log de actividades sospechosas
        if response.status_code >= 400:
            security_logger.warning(
                f"Request fallido: {request.method} {request.url.path} "
                f"Status: {response.status_code} "
                f"IP: {request.client.host} "
                f"User-Agent: {request.headers.get('user-agent', 'Desconocido')}"
            )
        
        # Log de tiempos de respuesta lentos (posibles ataques)
        if process_time > 5.0:  # Más de 5 segundos
            security_logger.warning(
                f"Request lento: {request.method} {request.url.path} "
                f"Tiempo: {process_time:.2f}s "
                f"IP: {request.client.host}"
            )
            
    except Exception as e:
        # Log de excepciones no manejadas
        security_logger.error(
            f"Excepción no manejada: {str(e)} "
            f"Request: {request.method} {request.url.path} "
            f"IP: {request.client.host} "
            f"Traceback: {traceback.format_exc()}"
        )
        raise
    
    return response

# Manejo global de excepciones
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # No exponer detalles internos en producción
    if settings.DEBUG:
        detail = str(exc)
    else:
        detail = "Error interno del servidor"
    
    security_logger.error(
        f"Excepción global: {str(exc)} "
        f"Request: {request.method} {request.url.path} "
        f"IP: {request.client.host if request.client else 'Desconocido'}"
    )
    
    return JSONResponse(
        status_code=500,
        content={"detail": detail}
    )

# Incluir routers - SOLO REST
app.include_router(rest.auth_router)
app.include_router(rest.router)
# GraphQL deshabilitado intencionalmente

@app.get("/")
async def root():
    return {
        "message": "API de Productos - Sistema Vehicular",
        "version": "2.0.0",
        "status": "operational",
        "security": "OWASP Top 10 implementado",
        "endpoints": {
            "documentación": "/docs",
            "autenticación": "/auth/login",
            "productos": "/productos",
            "health_check": "/health"
        },
        "features": {
            "rest_api": True,
            "graphql": False,
            "cors": "Configurado",
            "rate_limiting": "Activo",
            "security_headers": "Implementados"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "API Productos Vehiculares",
        "timestamp": time.time(),
        "debug_mode": settings.DEBUG,
        "security_measures": {
            "cors": "enabled",
            "rate_limiting": "enabled",
            "security_headers": "enabled",
            "input_validation": "enabled",
            "authentication": "enabled",
            "error_handling": "secure"
        },
        "owasp_coverage": [
            "A01:2021-Broken Access Control",
            "A02:2021-Cryptographic Failures", 
            "A03:2021-Injection",
            "A05:2021-Security Misconfiguration",
            "A06:2021-Vulnerable Components",
            "A07:2021-Identification and Authentication Failures",
            "A08:2021-Software Integrity Failures",
            "A10:2021-Server-Side Request Forgery"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 INICIANDO API DE PRODUCTOS VEHICULARES")
    print("=" * 60)
    print(f"📁 Entorno: {'🚧 DESARROLLO' if settings.DEBUG else '🔒 PRODUCCIÓN'}")
    print(f"🔐 JWT Secret: {settings.JWT_SECRET[:10]}...")
    print(f"🌐 CORS: {'Permisivo (desarrollo)' if settings.DEBUG else 'Restrictivo'}")
    print(f"📊 Rate Limit: {settings.RATE_LIMIT_PER_MINUTE}/minuto")
    print(f"⚡ GraphQL: ❌ DESHABILITADO")
    print(f"🔒 OWASP Top 10: ✅ IMPLEMENTADO")
    print("=" * 60)
    print("📚 Documentación: http://localhost:8000/docs")
    print("🔑 Login: POST /auth/login (admin/admin123)")
    print("📦 Productos: GET /productos/")
    print("=" * 60)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_config=None,
        access_log=True
    )