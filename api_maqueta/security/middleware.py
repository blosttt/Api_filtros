# security/middleware.py
import time
from typing import Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

logger = logging.getLogger("security")

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Headers de seguridad OWASP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # CSP básico
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self'"
        )
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts: Dict[str, Any] = {}
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Limpiar registros antiguos
        self.request_counts = {
            ip: data for ip, data in self.request_counts.items()
            if current_time - data["timestamp"] < 60
        }
        
        # Contar requests
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = {
                "count": 0,
                "timestamp": current_time
            }
        
        self.request_counts[client_ip]["count"] += 1
        
        # Verificar límite
        if self.request_counts[client_ip]["count"] > self.requests_per_minute:
            logger.warning(f"Rate limit excedido para IP: {client_ip}")
            return Response(
                content='{"detail": "Too many requests"}',
                status_code=429,
                media_type="application/json"
            )
        
        response = await call_next(request)
        return response