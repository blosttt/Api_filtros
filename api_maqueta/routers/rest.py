import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta

from database import get_db
from services.product_service import ProductService
from services.category_service import CategoryService
from filters.vehicle_filters import VehicleFilter
import schemas
from config import settings

# Configurar logger de seguridad
security_logger = logging.getLogger("security")

# --- AUTENTICACIÓN Y AUTORIZACIÓN MEJORADA ---

class RBAC:
    """Control de Acceso Basado en Roles"""
    
    ROLES = {
        "admin": ["create", "read", "update", "delete"],
        "manager": ["create", "read", "update"],
        "viewer": ["read"]
    }
    
    @staticmethod
    def has_permission(role: str, permission: str) -> bool:
        """Verifica si un rol tiene un permiso específico"""
        return role in RBAC.ROLES and permission in RBAC.ROLES[role]

def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer(auto_error=False))
):
    """
    Verificación robusta de token JWT con logging de seguridad
    """
    if not credentials:
        security_logger.warning("Intento de acceso sin token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Decodificar y validar token JWT
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        username = payload.get("sub")
        role = payload.get("role", "viewer")
        exp = payload.get("exp")
        
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido: usuario no especificado"
            )
        
        # Verificar expiración
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            security_logger.warning(f"Token expirado para usuario: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expirado"
            )
        
        # Log de acceso exitoso (solo para operaciones críticas)
        security_logger.info(f"Acceso autorizado para usuario: {username}, rol: {role}")
        
        return {
            "username": username,
            "role": role,
            "payload": payload
        }
        
    except JWTError as e:
        security_logger.warning(f"Error de validación de token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

def require_role(required_role: str):
    """Dependencia para requerir un rol específico"""
    def role_checker(auth: dict = Depends(verify_token)):
        if auth["role"] != required_role:
            security_logger.warning(
                f"Intento de acceso no autorizado: "
                f"usuario={auth['username']}, "
                f"rol_actual={auth['role']}, "
                f"rol_requerido={required_role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permisos insuficientes"
            )
        return auth
    return role_checker

def require_permission(permission: str):
    """Dependencia para requerir un permiso específico"""
    def permission_checker(auth: dict = Depends(verify_token)):
        if not RBAC.has_permission(auth["role"], permission):
            security_logger.warning(
                f"Intento de acceso sin permiso: "
                f"usuario={auth['username']}, "
                f"rol={auth['role']}, "
                f"permiso_requerido={permission}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permisos insuficientes"
            )
        return auth
    return permission_checker

# --- VALIDACIÓN DE PARÁMETROS MEJORADA ---

def validate_pagination_params(skip: int = 0, limit: int = Query(100, ge=1, le=1000)):
    """Valida parámetros de paginación con límites seguros"""
    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El parámetro 'skip' no puede ser negativo"
        )
    if limit > 1000:
        limit = 1000  # Límite máximo para prevenir DoS
    return skip, limit

def validate_vehicle_filter_params(
    tipo_vehiculo: Optional[str] = Query(None, max_length=20),
    tipo_aceite: Optional[str] = Query(None, max_length=20),
    tipo_combustible: Optional[str] = Query(None, max_length=20),
    tipo_filtro: Optional[str] = Query(None, max_length=20)
):
    """Valida y sanitiza parámetros de filtros vehiculares"""
    # Listas permitidas para prevenir inyección
    allowed_vehicle_types = ["auto", "moto", "camion", "bus", None]
    allowed_oil_types = ["sintetico", "mineral", "semi-sintetico", None]
    allowed_fuel_types = ["gasolina", "diesel", "electrico", "hibrido", None]
    allowed_filter_types = ["aire", "aceite", "combustible", "polen", "habitaculo", None]
    
    # Validar valores permitidos
    if tipo_vehiculo and tipo_vehiculo.lower() not in allowed_vehicle_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de vehículo no válido. Valores permitidos: {', '.join(filter(None, allowed_vehicle_types))}"
        )
    
    if tipo_aceite and tipo_aceite.lower() not in allowed_oil_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de aceite no válido. Valores permitidos: {', '.join(filter(None, allowed_oil_types))}"
        )
    
    if tipo_combustible and tipo_combustible.lower() not in allowed_fuel_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de combustible no válido. Valores permitidos: {', '.join(filter(None, allowed_fuel_types))}"
        )
    
    if tipo_filtro and tipo_filtro.lower() not in allowed_filter_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de filtro no válido. Valores permitidos: {', '.join(filter(None, allowed_filter_types))}"
        )
    
    return {
        "tipo_vehiculo": tipo_vehiculo.lower() if tipo_vehiculo else None,
        "tipo_aceite": tipo_aceite.lower() if tipo_aceite else None,
        "tipo_combustible": tipo_combustible.lower() if tipo_combustible else None,
        "tipo_filtro": tipo_filtro.lower() if tipo_filtro else None
    }

# --- DEPENDENCIAS DE SERVICIOS ---

def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(db)

def get_category_service(db: Session = Depends(get_db)) -> CategoryService:
    return CategoryService(db)

# --- ROUTER DE AUTENTICACIÓN ---
auth_router = APIRouter(prefix="/auth", tags=["Autenticación"])

@auth_router.post("/login")
async def login(username: str, password: str):
    """
    Endpoint de login para obtener token JWT
    """
    if username == "admin" and password == "admin123":
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data = {
            "sub": username,
            "role": "admin",
            "exp": expire
        }
        token = jwt.encode(token_data, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        
        security_logger.info(f"Login exitoso: usuario={username}")
        
        return {"access_token": token, "token_type": "bearer"}
    
    security_logger.warning(f"Intento de login fallido: usuario={username}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales incorrectas"
    )

# --- ROUTER PRINCIPAL DE PRODUCTOS ---
router = APIRouter(prefix="/productos", tags=["Productos"])

# --- ENDPOINTS PARA PRODUCTOS ---

@router.get("/", response_model=schemas.ProductoListResponse)
async def get_all_productos(
    skip: int = 0,
    limit: int = Query(100, ge=1, le=1000),
    categoria_id: Optional[int] = Query(None, ge=1),
    distribuidor_id: Optional[int] = Query(None, ge=1),
    service: ProductService = Depends(get_product_service),
    auth: dict = Depends(verify_token)
):
    """
    GET ALL - Obtener todos los productos con filtros opcionales
    Requiere autenticación
    """
    # Validar paginación
    skip, limit = validate_pagination_params(skip, limit)
    
    try:
        if categoria_id:
            productos = service.filtrar_por_categoria(categoria_id, skip, limit)
            total = service.count_by_categoria(categoria_id) if hasattr(service, 'count_by_categoria') else len(productos)
        elif distribuidor_id:
            productos = service.filtrar_por_distribuidor(distribuidor_id, skip, limit)
            total = service.count_by_distribuidor(distribuidor_id) if hasattr(service, 'count_by_distribuidor') else len(productos)
        else:
            productos = service.get_all(skip=skip, limit=limit)
            total = service.count_all()
        
        # Log de consulta exitosa
        security_logger.info(
            f"Consulta productos: usuario={auth['username']}, "
            f"categoria_id={categoria_id}, distribuidor_id={distribuidor_id}, "
            f"skip={skip}, limit={limit}, resultados={len(productos)}"
        )
        
        return schemas.ProductoListResponse(
            items=productos,
            total=total,
            pagina=skip // limit + 1 if limit > 0 else 1,
            tamaño=limit
        )
        
    except Exception as e:
        security_logger.error(f"Error en consulta productos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener productos"
        )

@router.get("/filtros-vehiculos")
async def get_filtros_vehiculos(auth: dict = Depends(verify_token)):
    """
    Obtener los filtros disponibles para productos vehiculares
    Requiere autenticación
    """
    return VehicleFilter.get_available_filters()

@router.get("/filtrar-vehiculos", response_model=schemas.ProductoListResponse)
async def filtrar_productos_vehiculares(
    tipo_vehiculo: Optional[str] = Query(None, max_length=20),
    tipo_aceite: Optional[str] = Query(None, max_length=20),
    tipo_combustible: Optional[str] = Query(None, max_length=20),
    tipo_filtro: Optional[str] = Query(None, max_length=20),
    skip: int = 0,
    limit: int = Query(100, ge=1, le=500),
    service: ProductService = Depends(get_product_service),
    auth: dict = Depends(verify_token)
):
    """
    Filtrar productos por características vehiculares
    Requiere autenticación
    """
    # Validar y sanitizar parámetros
    filtros_validados = validate_vehicle_filter_params(
        tipo_vehiculo, tipo_aceite, tipo_combustible, tipo_filtro
    )
    
    # Validar paginación
    skip, limit = validate_pagination_params(skip, limit)
    
    try:
        # Convertir a schema de filtro
        filtros = schemas.FiltroVehiculo(**filtros_validados)
        
        productos = service.filtrar_por_vehiculo(filtros, skip, limit)
        
        # Log de filtrado
        security_logger.info(
            f"Filtrado vehicular: usuario={auth['username']}, "
            f"filtros={filtros_validados}, "
            f"resultados={len(productos)}"
        )
        
        return schemas.ProductoListResponse(
            items=productos,
            total=len(productos),
            pagina=skip // limit + 1 if limit > 0 else 1,
            tamaño=limit
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        security_logger.error(f"Error en filtrado vehicular: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al filtrar productos"
        )

@router.get("/{producto_id}", response_model=schemas.ProductoResponse)
async def get_producto_by_id(
    producto_id: int,
    service: ProductService = Depends(get_product_service),
    auth: dict = Depends(verify_token)
):
    """
    GET by ID - Obtener un producto por su ID
    Requiere autenticación
    """
    try:
        producto = service.get_by_id(producto_id)
        if not producto:
            security_logger.warning(
                f"Producto no encontrado: usuario={auth['username']}, "
                f"producto_id={producto_id}"
            )
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        return producto
    except Exception as e:
        security_logger.error(f"Error obteniendo producto por ID: {str(e)}")
        raise

@router.get("/codigo-barras/{codigo_barras}", response_model=schemas.ProductoResponse)
async def get_producto_by_codigo_barras(
    codigo_barras: str,
    service: ProductService = Depends(get_product_service),
    auth: dict = Depends(verify_token)
):
    """
    GET by código de barras - Obtener un producto por su código de barras
    Requiere autenticación
    """
    # Validar formato del código de barras
    if not codigo_barras.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código de barras no puede estar vacío"
        )
    
    try:
        producto = service.get_by_codigo_barras(codigo_barras)
        if not producto:
            security_logger.warning(
                f"Producto no encontrado por código: usuario={auth['username']}, "
                f"codigo_barras={codigo_barras}"
            )
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        return producto
    except Exception as e:
        security_logger.error(f"Error obteniendo producto por código: {str(e)}")
        raise

@router.post("/", response_model=schemas.ProductoResponse)
async def create_producto(
    producto: schemas.ProductoCreate,
    service: ProductService = Depends(get_product_service),
    auth: dict = Depends(require_permission("create"))
):
    """
    POST - Crear un nuevo producto
    Requiere permiso 'create' (admin o manager)
    """
    try:
        # Log de creación
        security_logger.info(
            f"Creando producto: usuario={auth['username']}, "
            f"producto={producto.nombre}, codigo={producto.codigo_barras}"
        )
        
        nuevo_producto = service.create(producto)
        
        security_logger.info(
            f"Producto creado exitosamente: ID={nuevo_producto.id}, "
            f"usuario={auth['username']}"
        )
        
        return nuevo_producto
        
    except ValueError as e:
        security_logger.warning(
            f"Error de validación al crear producto: {str(e)}, "
            f"usuario={auth['username']}"
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        security_logger.error(f"Error interno al crear producto: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear producto"
        )

@router.put("/{producto_id}", response_model=schemas.ProductoResponse)
async def update_producto(
    producto_update: schemas.ProductoUpdate,
    producto_id: int,
    service: ProductService = Depends(get_product_service),
    auth: dict = Depends(require_permission("update"))
):
    """
    PUT - Actualizar completamente un producto
    Requiere permiso 'update' (admin o manager)
    """
    try:
        security_logger.info(
            f"Actualizando producto: usuario={auth['username']}, "
            f"producto_id={producto_id}"
        )
        
        producto_actualizado = service.update(producto_id, producto_update)
        if not producto_actualizado:
            security_logger.warning(
                f"Producto no encontrado para actualizar: "
                f"usuario={auth['username']}, producto_id={producto_id}"
            )
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        
        security_logger.info(
            f"Producto actualizado exitosamente: ID={producto_id}, "
            f"usuario={auth['username']}"
        )
        
        return producto_actualizado
    except Exception as e:
        security_logger.error(f"Error al actualizar producto: {str(e)}")
        raise

@router.patch("/{producto_id}", response_model=schemas.ProductoResponse)
async def partial_update_producto(
    producto_update: schemas.ProductoUpdate,
    producto_id: int,
    service: ProductService = Depends(get_product_service),
    auth: dict = Depends(require_permission("update"))
):
    """
    PATCH - Actualizar parcialmente un producto
    Requiere permiso 'update' (admin o manager)
    """
    try:
        security_logger.info(
            f"Actualizando parcialmente producto: usuario={auth['username']}, "
            f"producto_id={producto_id}"
        )
        
        producto_actualizado = service.partial_update(producto_id, producto_update)
        if not producto_actualizado:
            security_logger.warning(
                f"Producto no encontrado para actualización parcial: "
                f"usuario={auth['username']}, producto_id={producto_id}"
            )
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        
        return producto_actualizado
    except Exception as e:
        security_logger.error(f"Error al actualizar parcialmente producto: {str(e)}")
        raise

@router.delete("/{producto_id}")
async def delete_producto(
    producto_id: int,
    service: ProductService = Depends(get_product_service),
    auth: dict = Depends(require_role("admin"))
):
    """
    DELETE - Eliminar un producto (soft delete)
    Requiere rol 'admin'
    """
    try:
        security_logger.warning(
            f"Eliminando producto: usuario={auth['username']}, "
            f"producto_id={producto_id}"
        )
        
        if service.delete(producto_id):
            security_logger.warning(
                f"Producto eliminado: ID={producto_id}, "
                f"usuario={auth['username']}"
            )
            return {"message": "Producto eliminado correctamente"}
        else:
            security_logger.warning(
                f"Intento de eliminar producto no encontrado: "
                f"usuario={auth['username']}, producto_id={producto_id}"
            )
            raise HTTPException(status_code=404, detail="Producto no encontrado")
    except Exception as e:
        security_logger.error(f"Error al eliminar producto: {str(e)}")
        raise

# --- ENDPOINTS PARA CATEGORÍAS ---

@router.get("/categorias/", response_model=List[schemas.CategoriaResponse])
async def get_categorias(
    tipo: Optional[str] = Query(None, max_length=20),
    service: CategoryService = Depends(get_category_service),
    auth: dict = Depends(verify_token)
):
    """
    Obtener todas las categorías
    Requiere autenticación
    """
    try:
        if tipo:
            # Validar tipo de categoría
            allowed_types = ["vehiculo", "general", "repuesto", "lubricante"]
            if tipo.lower() not in allowed_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tipo de categoría no válido. Valores permitidos: {', '.join(allowed_types)}"
                )
            return service.get_by_tipo(tipo)
        return service.get_all()
    except Exception as e:
        security_logger.error(f"Error obteniendo categorías: {str(e)}")
        raise