# models.py - VERSIÓN COMPATIBLE
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base  # ← Importar Base desde database

# Tabla de categorías
class Categoria(Base):
    __tablename__ = "categorias"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, index=True, nullable=False)
    descripcion = Column(Text, nullable=True)
    tipo = Column(String(20), default="general")
    created_at = Column(DateTime, default=datetime.utcnow)
    activo = Column(Integer, default=1)

# Tabla de distribuidores
class Distribuidor(Base):
    __tablename__ = "distribuidores"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    contacto = Column(String(100))
    telefono = Column(String(20))
    email = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    activo = Column(Integer, default=1)

# Tabla principal de productos
class Producto(Base):
    __tablename__ = "productos"
    
    id = Column(Integer, primary_key=True, index=True)
    codigo_barras = Column(String(50), unique=True, index=True, nullable=False)
    nombre = Column(String(100), index=True, nullable=False)
    descripcion = Column(Text, nullable=True)
    marca = Column(String(50), nullable=False)
    
    # Relaciones
    categoria_id = Column(Integer, ForeignKey("categorias.id"))
    distribuidor_id = Column(Integer, ForeignKey("distribuidores.id"))
    
    # Campos de cantidad y precios
    cantidad = Column(Integer, default=0)
    precio_neto = Column(Float, nullable=False)
    porcentaje_ganancia = Column(Float, default=30.0)
    iva = Column(Float, default=19.0)
    precio_venta = Column(Float, nullable=False)
    
    # Campos específicos para filtros de vehículos
    tipo_vehiculo = Column(String(20), nullable=True)
    tipo_aceite = Column(String(20), nullable=True)
    tipo_combustible = Column(String(20), nullable=True)
    tipo_filtro = Column(String(20), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    activo = Column(Integer, default=1)
    
    # Relationships (sin backref para compatibilidad)
    categoria = relationship("Categoria")
    distribuidor = relationship("Distribuidor")

    def calcular_precio_venta(self):
        """Calcula el precio de venta automáticamente"""
        ganancia = self.precio_neto * (self.porcentaje_ganancia / 100)
        iva_calculado = (self.precio_neto + ganancia) * (self.iva / 100)
        return self.precio_neto + ganancia + iva_calculado