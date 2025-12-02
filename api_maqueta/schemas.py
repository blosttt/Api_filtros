from pydantic import BaseModel, validator, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# Schema base para categorías
class CategoriaBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    tipo: str = "general"

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaResponse(CategoriaBase):
    id: int
    created_at: datetime
    activo: int

    class Config:
        from_attributes = True

# Schema base para distribuidores
class DistribuidorBase(BaseModel):
    nombre: str
    contacto: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None

class DistribuidorCreate(DistribuidorBase):
    pass

class DistribuidorResponse(DistribuidorBase):
    id: int
    created_at: datetime
    activo: int

    class Config:
        from_attributes = True

# Schema base para productos
class ProductoBase(BaseModel):
    codigo_barras: str
    nombre: str
    descripcion: Optional[str] = None
    marca: str
    categoria_id: int
    distribuidor_id: Optional[int] = None
    cantidad: int = 0
    precio_neto: float
    porcentaje_ganancia: float = 30.0
    iva: float = 19.0
    
    # Campos para filtros de vehículos
    tipo_vehiculo: Optional[str] = None
    tipo_aceite: Optional[str] = None
    tipo_combustible: Optional[str] = None
    tipo_filtro: Optional[str] = None

    @field_validator('precio_neto')
    @classmethod
    def precio_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('El precio neto debe ser mayor a 0')
        return v

    @field_validator('porcentaje_ganancia')
    @classmethod
    def ganancia_must_be_reasonable(cls, v):
        if v < 0 or v > 1000:
            raise ValueError('El porcentaje de ganancia debe ser entre 0 y 1000')
        return v

    @field_validator('cantidad')
    @classmethod
    def cantidad_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('La cantidad no puede ser negativa')
        return v

class ProductoCreate(ProductoBase):
    pass

class ProductoUpdate(BaseModel):
    codigo_barras: Optional[str] = None
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    marca: Optional[str] = None
    categoria_id: Optional[int] = None
    distribuidor_id: Optional[int] = None
    cantidad: Optional[int] = None
    precio_neto: Optional[float] = None
    porcentaje_ganancia: Optional[float] = None
    iva: Optional[float] = None
    tipo_vehiculo: Optional[str] = None
    tipo_aceite: Optional[str] = None
    tipo_combustible: Optional[str] = None
    tipo_filtro: Optional[str] = None

class ProductoResponse(ProductoBase):
    id: int
    precio_venta: float
    created_at: datetime
    updated_at: datetime
    activo: int
    categoria: Optional[CategoriaResponse] = None
    distribuidor: Optional[DistribuidorResponse] = None

    class Config:
        from_attributes = True

class ProductoListResponse(BaseModel):
    items: List[ProductoResponse]
    total: int
    pagina: int
    tamaño: int

# Schemas para filtros
class FiltroVehiculo(BaseModel):
    tipo_vehiculo: Optional[str] = None
    tipo_aceite: Optional[str] = None
    tipo_combustible: Optional[str] = None
    tipo_filtro: Optional[str] = None