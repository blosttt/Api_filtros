from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from service.product_service import ProductService
from service.category_service import CategoryService
import schemas

# Dependencia de autenticación
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    if credentials.credentials != "secreto123":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado"
        )
    return True

# Dependencias de servicios
def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(db)

def get_category_service(db: Session = Depends(get_db)) -> CategoryService:
    return CategoryService(db)

# Router principal
router = APIRouter(prefix="/filtros", tags=["Filtros"])

# Endpoints para filtros (productos)
@router.get("/", response_model=schemas.FiltroListResponse)
async def get_all_filtros(
    skip: int = 0,
    limit: int = 100,
    categoria_id: Optional[int] = Query(None),
    distribuidor_id: Optional[int] = Query(None),
    service: ProductService = Depends(get_product_service)
):
    """GET ALL - Obtener todos los filtros con filtros opcionales"""
    if categoria_id:
        filtros = service.filtrar_por_categoria(categoria_id, skip, limit)
        total = len(filtros)  # Simplificado para el ejemplo
    elif distribuidor_id:
        filtros = service.filtrar_por_distribuidor(distribuidor_id, skip, limit)
        total = len(filtros)
    else:
        filtros = service.get_all(skip=skip, limit=limit)
        total = service.count_all()
    
    return schemas.FiltroListResponse(
        items=filtros,
        total=total,
        pagina=skip // limit + 1 if limit > 0 else 1,
        tamaño=limit
    )


@router.get("/{filtro_id}", response_model=schemas.FiltroResponse)
async def get_filtro_by_id(
    filtro_id: int,
    service: ProductService = Depends(get_product_service)
):
    """GET by ID - Obtener un filtro por su ID"""
    filtro = service.get_by_id(filtro_id)
    if not filtro:
        raise HTTPException(status_code=404, detail="Filtro no encontrado")
    return filtro

@router.get("/codigo-producto/{codigo_producto}", response_model=schemas.FiltroResponse)
async def get_filtro_by_codigo_producto(
    codigo_producto: str,
    service: ProductService = Depends(get_product_service)
):
    """GET by código de producto - Obtener un filtro por su código de producto"""
    filtro = service.get_by_codigo_producto(codigo_producto)
    if not filtro:
        raise HTTPException(status_code=404, detail="Filtro no encontrado")
    return filtro

@router.post("/", response_model=schemas.FiltroResponse)
async def create_filtro(
    filtro: schemas.FiltroCreate,
    service: ProductService = Depends(get_product_service),
    token_valid: bool = Depends(verify_token)
):
    """POST - Crear un nuevo filtro (Protegido con JWT)"""
    try:
        return service.create(filtro)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{filtro_id}", response_model=schemas.FiltroResponse)
async def update_filtro(
    filtro_id: int,
    filtro_update: schemas.FiltroUpdate,
    service: ProductService = Depends(get_product_service)
):
    """PUT - Actualizar completamente un filtro"""
    filtro_actualizado = service.update(filtro_id, filtro_update)
    if not filtro_actualizado:
        raise HTTPException(status_code=404, detail="Filtro no encontrado")
    return filtro_actualizado

@router.patch("/{filtro_id}", response_model=schemas.FiltroResponse)
async def partial_update_filtro(
    filtro_id: int,
    filtro_update: schemas.FiltroUpdate,
    service: ProductService = Depends(get_product_service)
):
    """PATCH - Actualizar parcialmente un filtro"""
    filtro_actualizado = service.partial_update(filtro_id, filtro_update)
    if not filtro_actualizado:
        raise HTTPException(status_code=404, detail="Filtro no encontrado")
    return filtro_actualizado

@router.delete("/{filtro_id}")
async def delete_filtro(
    filtro_id: int,
    service: ProductService = Depends(get_product_service)
):
    """DELETE - Eliminar un filtro"""
    if service.delete(filtro_id):
        return {"message": "Filtro eliminado correctamente"}
    else:
        raise HTTPException(status_code=404, detail="Filtro no encontrado")

# Endpoints para categorías
@router.get("/categorias/", response_model=List[schemas.CategoriaResponse])
async def get_categorias(
    service: CategoryService = Depends(get_category_service)
):
    """Obtener todas las categorías"""
    return service.get_all()