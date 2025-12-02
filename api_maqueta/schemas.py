from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date
from decimal import Decimal

# ==============================
# SCHEMAS PARA CATEGORIAS
# ==============================
class CategoriaBase(BaseModel):
    nombre_categoria: str

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaResponse(CategoriaBase):
    id_categoria: int

    class Config:
        from_attributes = True

# ==============================
# SCHEMAS PARA DISTRIBUIDORES
# ==============================
class DistribuidorBase(BaseModel):
    nombre: str
    rut: str
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None

class DistribuidorCreate(DistribuidorBase):
    pass

class DistribuidorResponse(DistribuidorBase):
    id_distribuidor: int

    class Config:
        from_attributes = True

# ==============================
# SCHEMAS PARA FILTROS (PRODUCTOS)
# ==============================
class FiltroBase(BaseModel):
    codigo_producto: str
    nombre_filtro: str
    id_categoria: int
    marca: str
    descripcion: Optional[str] = None
    precio_compra: Decimal
    margen_ganancia: Decimal = 30.0
    stock: int = 0
    id_distribuidor: Optional[int] = None

    @field_validator('precio_compra')
    @classmethod
    def precio_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('El precio de compra debe ser mayor a 0')
        return v

    @field_validator('margen_ganancia')
    @classmethod
    def ganancia_must_be_reasonable(cls, v):
        if v < 0 or v > 1000:
            raise ValueError('El margen de ganancia debe ser entre 0 y 1000')
        return v

    @field_validator('stock')
    @classmethod
    def stock_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('El stock no puede ser negativo')
        return v

class FiltroCreate(FiltroBase):
    pass

class FiltroUpdate(BaseModel):
    codigo_producto: Optional[str] = None
    nombre_filtro: Optional[str] = None
    id_categoria: Optional[int] = None
    marca: Optional[str] = None
    descripcion: Optional[str] = None
    precio_compra: Optional[Decimal] = None
    margen_ganancia: Optional[Decimal] = None
    stock: Optional[int] = None
    id_distribuidor: Optional[int] = None

class FiltroResponse(FiltroBase):
    id_filtro: int
    precio_neto: Decimal
    iva: Decimal
    precio_venta: Decimal
    fecha_actualizacion: date
    categoria: Optional[CategoriaResponse] = None
    distribuidor: Optional[DistribuidorResponse] = None

    class Config:
        from_attributes = True

class FiltroListResponse(BaseModel):
    items: List[FiltroResponse]
    total: int
    pagina: int
    tamaño: int
