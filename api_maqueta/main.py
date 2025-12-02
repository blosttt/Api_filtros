from fastapi import FastAPI
import models
from database import engine
from routers import rest, graphql
from routers.graphql import graphql_router

# Crear tablas
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API de Filtros - Sistema Vehicular",
    description="API REST y GraphQL para gestión de filtros vehiculares",
    version="2.0.0"
)

# Incluir routers
app.include_router(rest.router)
app.include_router(graphql_router, prefix="/graphql")

@app.get("/")
async def root():
    return {
        "message": "API de Filtros - Sistema Vehicular",
        "caracteristicas": {
            "base_datos": {
                "filtros": "Código producto, nombre, descripción, marca, categoría, precios calculados",
                "categorias": "Sistema de categorías (Aire, Aceite, Combustible, Habitáculo)",
                "distribuidores": "Gestión de proveedores con RUT, dirección, ciudad"
            },
            "endpoints_rest": {
                "GET_ALL": "GET /filtros/",
                "GET_BY_ID": "GET /filtros/{filtro_id}",
                "GET_BY_CODIGO": "GET /filtros/codigo-producto/{codigo_producto}",
                "POST": "POST /filtros/ (Protegido con JWT)",
                "PUT": "PUT /filtros/{filtro_id}",
                "PATCH": "PATCH /filtros/{filtro_id}",
                "DELETE": "DELETE /filtros/{filtro_id}",
                "CATEGORIAS": "GET /filtros/categorias/"
            },
            "graphql": {
                "endpoint": "POST /graphql",
                "queries": ["filtros", "filtro", "categories"],
                "mutations": ["createFiltro"]
            }
        },
        "autenticacion": {
            "metodo": "Bearer Token",
            "token": "secreto123"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "API Filtros Vehiculares"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)