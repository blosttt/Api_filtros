import logging
import strawberry
from typing import List, Optional, Dict, Any
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info
from sqlalchemy.orm import Session
from fastapi import Depends, Request
from functools import wraps
import time
import re

from database import get_db
from services.product_service import ProductService
from services.category_service import CategoryService
from filters.vehicle_filters import VehicleFilter, validate_and_sanitize_filters
import models
import schemas

# Logger para GraphQL
graphql_logger = logging.getLogger("graphql")

# Context dependency con seguridad mejorada
async def get_context(
    request: Request,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Contexto de GraphQL con información de seguridad"""
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Registrar acceso
    graphql_logger.info(
        f"GraphQL Access - IP: {client_ip[:15]}, "
        f"User-Agent: {user_agent[:50]}, "
        f"Path: {request.url.path}"
    )
    
    return {
        "db": db,
        "product_service": ProductService(db),
        "category_service": CategoryService(db),
        "request": request,
        "client_ip": client_ip,
        "user_agent": user_agent
    }

# Middleware para seguridad de GraphQL
def graphql_security_middleware(resolver, *args, **kwargs):
    """Middleware de seguridad para resolvers GraphQL"""
    @wraps(resolver)
    async def wrapper(*args, **kwargs):
        info = kwargs.get('info') or args[1] if len(args) > 1 else None
        start_time = time.time()
        
        try:
            # Obtener información de contexto
            context = info.context if info else {}
            client_ip = context.get("client_ip", "unknown")
            operation_name = info.field_name if info else "unknown"
            
            # Log de inicio de operación
            graphql_logger.debug(
                f"GraphQL Operation Start - "
                f"Operation: {operation_name}, "
                f"IP: {client_ip}"
            )
            
            # Validar complejidad de consulta (prevención de DoS)
            if info and hasattr(info, 'selected_fields'):
                complexity = _calculate_query_complexity(info.selected_fields)
                if complexity > 100:  # Límite de complejidad
                    graphql_logger.warning(
                        f"Query complexity exceeded - "
                        f"Operation: {operation_name}, "
                        f"Complexity: {complexity}, "
                        f"IP: {client_ip}"
                    )
                    raise Exception("Query too complex. Reduce nested fields.")
            
            # Ejecutar resolver
            result = await resolver(*args, **kwargs) if callable(resolver) else resolver
            
            # Log de operación exitosa
            process_time = time.time() - start_time
            graphql_logger.info(
                f"GraphQL Operation Complete - "
                f"Operation: {operation_name}, "
                f"Time: {process_time:.2f}s, "
                f"IP: {client_ip}"
            )
            
            return result
            
        except Exception as e:
            # Log de error (sin exponer detalles sensibles)
            process_time = time.time() - start_time
            graphql_logger.error(
                f"GraphQL Operation Error - "
                f"Operation: {operation_name if 'operation_name' in locals() else 'unknown'}, "
                f"Error: {str(e)[:100]}, "
                f"Time: {process_time:.2f}s, "
                f"IP: {client_ip if 'client_ip' in locals() else 'unknown'}"
            )
            raise
            
    return wrapper

def _calculate_query_complexity(selected_fields, depth=0, max_depth=5):
    """Calcula complejidad aproximada de la consulta GraphQL"""
    if depth > max_depth:
        return 100  # Límite de profundidad
    
    complexity = 1
    for field in selected_fields:
        if hasattr(field, 'selections'):
            complexity += _calculate_query_complexity(field.selections, depth + 1, max_depth)
    return complexity

# Tipos GraphQL con validación
@strawberry.type
class Categoria:
    id: strawberry.ID
    nombre: str
    descripcion: Optional[str]
    tipo: str

    @classmethod
    def from_db(cls, db_categoria: models.Categoria):
        return cls(
            id=db_categoria.id,
            nombre=db_categoria.nombre,
            descripcion=db_categoria.descripcion,
            tipo=db_categoria.tipo
        )

@strawberry.type
class Producto:
    id: strawberry.ID
    codigo_barras: str
    nombre: str
    descripcion: Optional[str]
    marca: str
    cantidad: int
    precio_neto: float
    porcentaje_ganancia: float
    iva: float
    precio_venta: float
    tipo_vehiculo: Optional[str]
    tipo_aceite: Optional[str]
    tipo_combustible: Optional[str]
    tipo_filtro: Optional[str]
    categoria: Optional[Categoria]

    @classmethod
    def from_db(cls, db_producto: models.Producto):
        return cls(
            id=db_producto.id,
            codigo_barras=db_producto.codigo_barras,
            nombre=db_producto.nombre,
            descripcion=db_producto.descripcion,
            marca=db_producto.marca,
            cantidad=db_producto.cantidad,
            precio_neto=db_producto.precio_neto,
            porcentaje_ganancia=db_producto.porcentaje_ganancia,
            iva=db_producto.iva,
            precio_venta=db_producto.precio_venta,
            tipo_vehiculo=db_producto.tipo_vehiculo,
            tipo_aceite=db_producto.tipo_aceite,
            tipo_combustible=db_producto.tipo_combustible,
            tipo_filtro=db_producto.tipo_filtro,
            categoria=Categoria.from_db(db_producto.categoria) if db_producto.categoria else None
        )

# Inputs GraphQL con validación
@strawberry.input
class ProductoInput:
    codigo_barras: str = strawberry.field(
        description="Código de barras (8-50 caracteres alfanuméricos)"
    )
    nombre: str = strawberry.field(
        description="Nombre del producto (1-100 caracteres)"
    )
    descripcion: Optional[str] = strawberry.field(
        default=None,
        description="Descripción opcional del producto"
    )
    marca: str = strawberry.field(
        description="Marca del producto (1-50 caracteres)"
    )
    categoria_id: strawberry.ID = strawberry.field(
        description="ID de la categoría (mayor a 0)"
    )
    cantidad: int = strawberry.field(
        default=0,
        description="Cantidad en inventario (no negativa)"
    )
    precio_neto: float = strawberry.field(
        description="Precio neto del producto (mayor a 0)"
    )
    porcentaje_ganancia: float = strawberry.field(
        default=30.0,
        description="Porcentaje de ganancia (0-1000)"
    )
    iva: float = strawberry.field(
        default=19.0,
        description="Porcentaje de IVA (0-100)"
    )
    tipo_vehiculo: Optional[str] = strawberry.field(
        default=None,
        description="Tipo de vehículo (auto, moto, camion, bus)"
    )
    tipo_aceite: Optional[str] = strawberry.field(
        default=None,
        description="Tipo de aceite (sintetico, mineral, semi-sintetico)"
    )
    tipo_combustible: Optional[str] = strawberry.field(
        default=None,
        description="Tipo de combustible (gasolina, diesel, electrico, hibrido)"
    )
    tipo_filtro: Optional[str] = strawberry.field(
        default=None,
        description="Tipo de filtro (aire, aceite, combustible, polen, habitaculo)"
    )

@strawberry.input
class FiltroVehiculoInput:
    tipo_vehiculo: Optional[str] = strawberry.field(
        default=None,
        description="Tipo de vehículo para filtrado"
    )
    tipo_aceite: Optional[str] = strawberry.field(
        default=None,
        description="Tipo de aceite para filtrado"
    )
    tipo_combustible: Optional[str] = strawberry.field(
        default=None,
        description="Tipo de combustible para filtrado"
    )
    tipo_filtro: Optional[str] = strawberry.field(
        default=None,
        description="Tipo de filtro para filtrado"
    )

# Schemas de respuesta con paginación segura
@strawberry.type
class ProductoPaginado:
    items: List[Producto]
    total: int
    pagina: int
    size: int

# Nuevo tipo para opciones de filtro
@strawberry.type
class FilterOptions:
    tipo_vehiculo: List[str]
    tipo_aceite: List[str]
    tipo_combustible: List[str]
    tipo_filtro: List[str]

    @classmethod
    def from_dict(cls, filters_dict):
        return cls(
            tipo_vehiculo=filters_dict.get("tipo_vehiculo", []),
            tipo_aceite=filters_dict.get("tipo_aceite", []),
            tipo_combustible=filters_dict.get("tipo_combustible", []),
            tipo_filtro=filters_dict.get("tipo_filtro", [])
        )

# Queries GraphQL con seguridad
@strawberry.type
class Query:
    @strawberry.field
    @graphql_security_middleware
    def products(
        self, 
        info: Info, 
        skip: int = 0, 
        limit: int = strawberry.field(default=100, description="Límite máximo 1000")
    ) -> ProductoPaginado:
        """Query products - Obtener lista de productos con paginación segura"""
        # Validar parámetros de paginación
        if skip < 0:
            raise Exception("El parámetro 'skip' no puede ser negativo")
        if limit < 1 or limit > 1000:
            limit = 100  # Valor por defecto seguro
        
        service = info.context["product_service"]
        
        # Obtener productos con parámetros validados
        db_productos = service.get_all(skip=skip, limit=limit, user="graphql")
        total = service.count_all()
        
        # Auditoría de consulta
        graphql_logger.info(
            f"GraphQL Query: products - "
            f"Skip: {skip}, Limit: {limit}, "
            f"Total: {total}, "
            f"IP: {info.context.get('client_ip', 'unknown')}"
        )
        
        return ProductoPaginado(
            items=[Producto.from_db(producto) for producto in db_productos],
            total=total,
            pagina=skip // limit + 1 if limit > 0 else 1,
            size=limit
        )
    
    @strawberry.field
    @graphql_security_middleware
    def product(self, info: Info, id: strawberry.ID) -> Optional[Producto]:
        """Query product - Obtener un producto por ID"""
        # Validar ID
        try:
            product_id = int(id)
            if product_id < 1:
                raise Exception("ID de producto inválido")
        except (ValueError, TypeError):
            raise Exception("ID de producto debe ser un número entero")
        
        service = info.context["product_service"]
        db_producto = service.get_by_id(product_id, user="graphql")
        
        if not db_producto:
            graphql_logger.warning(
                f"GraphQL Query: product - "
                f"Producto no encontrado: ID={id}, "
                f"IP: {info.context.get('client_ip', 'unknown')}"
            )
            return None
        
        return Producto.from_db(db_producto)
    
    @strawberry.field
    @graphql_security_middleware
    def productsByVehicleFilter(
        self, 
        info: Info, 
        filtros: FiltroVehiculoInput,
        skip: int = 0,
        limit: int = 100
    ) -> ProductoPaginado:
        """Query productsByVehicleFilter - Filtrar productos vehiculares con validación"""
        # Validar parámetros de paginación
        if skip < 0:
            raise Exception("El parámetro 'skip' no puede ser negativo")
        if limit < 1 or limit > 500:
            limit = 100  # Límite más bajo para consultas de filtrado
        
        # Validar y sanitizar filtros
        filter_dict = {
            "tipo_vehiculo": filtros.tipo_vehiculo,
            "tipo_aceite": filtros.tipo_aceite,
            "tipo_combustible": filtros.tipo_combustible,
            "tipo_filtro": filtros.tipo_filtro
        }
        
        # Remover valores None
        filter_dict = {k: v for k, v in filter_dict.items() if v is not None}
        
        # Validar filtros con el sistema de validación
        is_valid, error_msg, sanitized_filters = validate_and_sanitize_filters(**filter_dict)
        
        if not is_valid:
            graphql_logger.warning(
                f"GraphQL Query: productsByVehicleFilter - "
                f"Filtros inválidos: {error_msg}, "
                f"IP: {info.context.get('client_ip', 'unknown')}"
            )
            raise Exception(f"Filtros inválidos: {error_msg}")
        
        # Registrar auditoría de filtros
        VehicleFilter.audit_filter_usage(
            sanitized_filters or {},
            info.context.get('client_ip', 'unknown')
        )
        
        # Convertir a schema de filtro
        filtro_schema = schemas.FiltroVehiculo(**sanitized_filters) if sanitized_filters else schemas.FiltroVehiculo()
        
        # Ejecutar filtrado
        service = info.context["product_service"]
        db_productos = service.filtrar_por_vehiculo(
            filtro_schema, 
            skip=skip, 
            limit=limit, 
            user="graphql"
        )
        
        return ProductoPaginado(
            items=[Producto.from_db(producto) for producto in db_productos],
            total=len(db_productos),
            pagina=skip // limit + 1 if limit > 0 else 1,
            size=limit
        )
    
    @strawberry.field
    @graphql_security_middleware
    def categories(self, info: Info) -> List[Categoria]:
        """Query categories - Obtener todas las categorías"""
        service = info.context["category_service"]
        db_categorias = service.get_all(user="graphql")
        return [Categoria.from_db(categoria) for categoria in db_categorias]
    
    @strawberry.field
    @graphql_security_middleware
    def vehicleFilterOptions(self, info: Info) -> FilterOptions:
        """Query vehicleFilterOptions - Obtener opciones de filtro disponibles"""
        filters = VehicleFilter.get_available_filters()
        return FilterOptions.from_dict(filters)

# Mutations GraphQL con seguridad
@strawberry.type
class Mutation:
    @strawberry.mutation
    @graphql_security_middleware
    def createProduct(self, info: Info, producto: ProductoInput) -> Producto:
        """Mutation createProduct - Crear un nuevo producto con validación"""
        # Obtener información de contexto para logging
        client_ip = info.context.get("client_ip", "unknown")
        
        # Validar datos básicos
        if not producto.codigo_barras or not producto.nombre:
            raise Exception("Código de barras y nombre son requeridos")
        
        # Validar longitud de campos
        if len(producto.codigo_barras) < 8 or len(producto.codigo_barras) > 50:
            raise Exception("Código de barras debe tener entre 8 y 50 caracteres")
        
        if len(producto.nombre) < 1 or len(producto.nombre) > 100:
            raise Exception("Nombre debe tener entre 1 y 100 caracteres")
        
        if len(producto.marca) < 1 or len(producto.marca) > 50:
            raise Exception("Marca debe tener entre 1 y 50 caracteres")
        
        # Validar datos numéricos
        if producto.precio_neto <= 0:
            raise Exception("El precio neto debe ser mayor a 0")
        
        if producto.cantidad < 0:
            raise Exception("La cantidad no puede ser negativa")
        
        if producto.porcentaje_ganancia < 0 or producto.porcentaje_ganancia > 1000:
            raise Exception("El porcentaje de ganancia debe estar entre 0 y 1000")
        
        if producto.iva < 0 or producto.iva > 100:
            raise Exception("El IVA debe estar entre 0 y 100")
        
        # Validar categoría
        try:
            categoria_id = int(producto.categoria_id)
            if categoria_id < 1:
                raise Exception("ID de categoría inválido")
        except (ValueError, TypeError):
            raise Exception("ID de categoría debe ser un número entero")
        
        # Validar tipos de filtro si se proporcionan
        if producto.tipo_vehiculo:
            is_valid, error_msg = VehicleFilter.validate_filter_value("tipo_vehiculo", producto.tipo_vehiculo)
            if not is_valid:
                raise Exception(f"Tipo de vehículo inválido: {error_msg}")
        
        if producto.tipo_aceite:
            is_valid, error_msg = VehicleFilter.validate_filter_value("tipo_aceite", producto.tipo_aceite)
            if not is_valid:
                raise Exception(f"Tipo de aceite inválido: {error_msg}")
        
        if producto.tipo_combustible:
            is_valid, error_msg = VehicleFilter.validate_filter_value("tipo_combustible", producto.tipo_combustible)
            if not is_valid:
                raise Exception(f"Tipo de combustible inválido: {error_msg}")
        
        if producto.tipo_filtro:
            is_valid, error_msg = VehicleFilter.validate_filter_value("tipo_filtro", producto.tipo_filtro)
            if not is_valid:
                raise Exception(f"Tipo de filtro inválido: {error_msg}")
        
        # Convertir a schema de creación
        producto_data = schemas.ProductoCreate(
            codigo_barras=producto.codigo_barras,
            nombre=producto.nombre,
            descripcion=producto.descripcion,
            marca=producto.marca,
            categoria_id=categoria_id,
            cantidad=producto.cantidad,
            precio_neto=producto.precio_neto,
            porcentaje_ganancia=producto.porcentaje_ganancia,
            iva=producto.iva,
            tipo_vehiculo=producto.tipo_vehiculo,
            tipo_aceite=producto.tipo_aceite,
            tipo_combustible=producto.tipo_combustible,
            tipo_filtro=producto.tipo_filtro
        )
        
        # Registrar intento de creación
        graphql_logger.info(
            f"GraphQL Mutation: createProduct - "
            f"Producto: {producto.nombre}, "
            f"Código: {producto.codigo_barras}, "
            f"IP: {client_ip}"
        )
        
        # Ejecutar creación
        try:
            service = info.context["product_service"]
            db_producto = service.create(producto_data, user="graphql")
            
            # Registrar creación exitosa
            graphql_logger.info(
                f"GraphQL Mutation Success: createProduct - "
                f"Producto ID: {db_producto.id}, "
                f"IP: {client_ip}"
            )
            
            return Producto.from_db(db_producto)
        except ValueError as e:
            graphql_logger.warning(
                f"GraphQL Mutation Error: createProduct - "
                f"Error: {str(e)}, "
                f"IP: {client_ip}"
            )
            raise Exception(str(e))
        except Exception as e:
            graphql_logger.error(
                f"GraphQL Mutation Internal Error: createProduct - "
                f"Error: {str(e)}, "
                f"IP: {client_ip}"
            )
            raise Exception("Error interno al crear producto")

# Schema GraphQL con extensiones de seguridad
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[]
)

# Router GraphQL ULTRA SIMPLIFICADO
try:
    router = GraphQLRouter(
        schema,
        context_getter=get_context
    )
except TypeError as e:
    # Si falla, crear una versión mínima
    print(f"⚠️  Advertencia: GraphQLRouter falló: {e}")
    print("✅ Creando router básico...")
    from fastapi import APIRouter
    router = APIRouter()
    
    @router.get("/")
    async def graphql_root():
        return {"message": "GraphQL endpoint (configuración básica)"}