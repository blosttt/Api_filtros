import strawberry
from typing import List, Optional
from strawberry.fastapi import GraphQLRouter
from sqlalchemy.orm import Session
from fastapi import Depends

from database import get_db
from service.product_service import ProductService
from service.category_service import CategoryService
import models
import schemas

# Context dependency
async def get_context(db: Session = Depends(get_db)):
    return {
        "db": db, 
        "product_service": ProductService(db),
        "category_service": CategoryService(db)
    }

# Tipos GraphQL
@strawberry.type
class Categoria:
    id_categoria: int
    nombre_categoria: str

    @classmethod
    def from_db(cls, db_categoria: models.Categorias):
        return cls(
            id_categoria=db_categoria.id_categoria,
            nombre_categoria=db_categoria.nombre_categoria
        )

@strawberry.type
class Filtro:
    id_filtro: int
    codigo_producto: str
    nombre_filtro: str
    marca: str
    descripcion: Optional[str]
    precio_compra: float
    margen_ganancia: float
    precio_neto: float
    iva: float
    precio_venta: float
    stock: int
    fecha_actualizacion: str
    categoria: Optional[Categoria]

    @classmethod
    def from_db(cls, db_filtro: models.Filtros):
        return cls(
            id_filtro=db_filtro.id_filtro,
            codigo_producto=db_filtro.codigo_producto,
            nombre_filtro=db_filtro.nombre_filtro,
            marca=db_filtro.marca,
            descripcion=db_filtro.descripcion,
            precio_compra=float(db_filtro.precio_compra),
            margen_ganancia=float(db_filtro.margen_ganancia),
            precio_neto=float(db_filtro.precio_neto),
            iva=float(db_filtro.iva),
            precio_venta=float(db_filtro.precio_venta),
            stock=db_filtro.stock,
            fecha_actualizacion=str(db_filtro.fecha_actualizacion),
            categoria=Categoria.from_db(db_filtro.categoria) if db_filtro.categoria else None
        )

# Inputs GraphQL
@strawberry.input
class FiltroInput:
    codigo_producto: str
    nombre_filtro: str
    id_categoria: int
    marca: str
    descripcion: Optional[str] = None
    precio_compra: float
    margen_ganancia: float = 30.0
    stock: int = 0
    id_distribuidor: Optional[int] = None


# Queries GraphQL
@strawberry.type
class Query:
    @strawberry.field
    def filtros(self, info, skip: int = 0, limit: int = 100) -> List[Filtro]:
        """Query filtros - Obtener lista de filtros"""
        service = info.context["product_service"]
        db_filtros = service.get_all(skip=skip, limit=limit)
        return [Filtro.from_db(filtro) for filtro in db_filtros]
    
    @strawberry.field
    def filtro(self, info, id: int) -> Optional[Filtro]:
        """Query filtro - Obtener un filtro por ID"""
        service = info.context["product_service"]
        db_filtro = service.get_by_id(id)
        return Filtro.from_db(db_filtro) if db_filtro else None
    
    
    @strawberry.field
    def categories(self, info) -> List[Categoria]:
        """Query categories - Obtener todas las categorías"""
        service = info.context["category_service"]
        db_categorias = service.get_all()
        return [Categoria.from_db(categoria) for categoria in db_categorias]

# Mutations GraphQL
@strawberry.type
class Mutation:
    @strawberry.mutation
    def createFiltro(self, info, filtro: FiltroInput) -> Filtro:
        """Mutation createFiltro - Crear un nuevo filtro"""
        service = info.context["product_service"]
        
        filtro_data = schemas.FiltroCreate(
            codigo_producto=filtro.codigo_producto,
            nombre_filtro=filtro.nombre_filtro,
            id_categoria=filtro.id_categoria,
            marca=filtro.marca,
            descripcion=filtro.descripcion,
            precio_compra=filtro.precio_compra,
            margen_ganancia=filtro.margen_ganancia,
            stock=filtro.stock,
            id_distribuidor=filtro.id_distribuidor
        )
        
        try:
            db_filtro = service.create(filtro_data)
            return Filtro.from_db(db_filtro)
        except ValueError as e:
            raise Exception(str(e))

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(schema, context_getter=get_context)