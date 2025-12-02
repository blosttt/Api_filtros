import logging
from sqlalchemy.orm import Session, Query
from sqlalchemy import and_, or_, func
from typing import List, Optional, Dict, Any, Tuple
import re
import models
import schemas

# Logger para operaciones de base de datos
db_logger = logging.getLogger("database")

class ProductService:
    def __init__(self, db: Session):
        self.db = db
        # Patrones regex para validación
        self.barcode_pattern = re.compile(r'^[A-Za-z0-9\-_]{8,50}$')
        self.name_pattern = re.compile(r'^[A-Za-z0-9\s\-_.,;:áéíóúÁÉÍÓÚñÑ]{1,100}$')
        self.brand_pattern = re.compile(r'^[A-Za-z0-9\s\-_&]{1,50}$')

    def _validate_input_parameters(self, **kwargs) -> Dict[str, Any]:
        """Valida y sanitiza parámetros de entrada"""
        validated = {}
        
        for key, value in kwargs.items():
            if value is None:
                validated[key] = None
                continue
                
            # Validaciones específicas por tipo de parámetro
            if key == 'skip' and value < 0:
                raise ValueError(f"El parámetro 'skip' no puede ser negativo: {value}")
            
            if key == 'limit':
                if value < 1:
                    raise ValueError(f"El parámetro 'limit' debe ser mayor a 0: {value}")
                if value > 1000:
                    value = 1000  # Limitar para prevenir DoS
                    db_logger.warning(f"Limit truncado a {value} por seguridad")
            
            if key == 'producto_id' and value < 1:
                raise ValueError(f"ID de producto inválido: {value}")
            
            if key == 'codigo_barras':
                if not isinstance(value, str):
                    raise ValueError("El código de barras debe ser una cadena")
                value = value.strip()
                if not self.barcode_pattern.match(value):
                    raise ValueError(f"Código de barras con formato inválido: {value}")
            
            if key == 'categoria_id' and value < 1:
                raise ValueError(f"ID de categoría inválido: {value}")
            
            if key == 'distribuidor_id' and value < 1:
                raise ValueError(f"ID de distribuidor inválido: {value}")
            
            validated[key] = value
        
        return validated

    def _log_query(self, operation: str, user: str = "system", **kwargs):
        """Log de operaciones de base de datos para auditoría"""
        db_logger.info(
            f"DB Operation: {operation}, User: {user}, "
            f"Params: {kwargs}"
        )

    def _sanitize_string(self, value: str) -> str:
        """Sanitiza cadenas para prevenir inyecciones"""
        if not value:
            return value
        
        # Remover caracteres peligrosos
        value = value.strip()
        value = re.sub(r'[\x00-\x1F\x7F]', '', value)  # Control characters
        value = re.sub(r'[\'"\\;]', '', value)  # Caracteres SQL peligrosos
        
        return value

    def get_all(self, skip: int = 0, limit: int = 100, user: str = "system") -> List[models.Producto]:
        """Obtener todos los productos con validación de parámetros"""
        try:
            params = self._validate_input_parameters(skip=skip, limit=limit)
            skip = params['skip']
            limit = params['limit']
            
            self._log_query("get_all", user, skip=skip, limit=limit)
            
            query = self.db.query(models.Producto).filter(
                models.Producto.activo == 1
            )
            
            # Ordenar por ID para paginación consistente
            query = query.order_by(models.Producto.id)
            
            result = query.offset(skip).limit(limit).all()
            
            db_logger.debug(f"Consulta get_all retornó {len(result)} registros")
            return result
            
        except ValueError as e:
            db_logger.error(f"Error de validación en get_all: {str(e)}")
            raise
        except Exception as e:
            db_logger.error(f"Error en get_all: {str(e)}")
            raise

    def get_by_id(self, producto_id: int, user: str = "system") -> Optional[models.Producto]:
        """Obtener producto por ID con validación"""
        try:
            params = self._validate_input_parameters(producto_id=producto_id)
            producto_id = params['producto_id']
            
            self._log_query("get_by_id", user, producto_id=producto_id)
            
            # Usar parámetros nombrados para prevenir inyección
            result = self.db.query(models.Producto).filter(
                and_(
                    models.Producto.id == producto_id,
                    models.Producto.activo == 1
                )
            ).first()
            
            if not result:
                db_logger.warning(f"Producto no encontrado: ID={producto_id}")
            
            return result
            
        except ValueError as e:
            db_logger.error(f"Error de validación en get_by_id: {str(e)}")
            raise
        except Exception as e:
            db_logger.error(f"Error en get_by_id: {str(e)}")
            raise

    def get_by_codigo_barras(self, codigo_barras: str, user: str = "system") -> Optional[models.Producto]:
        """Obtener producto por código de barras con validación"""
        try:
            params = self._validate_input_parameters(codigo_barras=codigo_barras)
            codigo_barras = params['codigo_barras']
            
            self._log_query("get_by_codigo_barras", user, codigo_barras=codigo_barras[:10])
            
            # Sanitizar código de barras
            codigo_barras = self._sanitize_string(codigo_barras)
            
            result = self.db.query(models.Producto).filter(
                and_(
                    models.Producto.codigo_barras == codigo_barras,
                    models.Producto.activo == 1
                )
            ).first()
            
            if not result:
                db_logger.debug(f"Código de barras no encontrado: {codigo_barras[:10]}...")
            
            return result
            
        except ValueError as e:
            db_logger.error(f"Error de validación en get_by_codigo_barras: {str(e)}")
            raise
        except Exception as e:
            db_logger.error(f"Error en get_by_codigo_barras: {str(e)}")
            raise

    def create(self, producto: schemas.ProductoCreate, user: str = "system") -> models.Producto:
        """Crear nuevo producto con validaciones extensivas"""
        try:
            self._log_query("create", user, producto_data=producto.model_dump())
            
            # Validar datos del producto
            if not producto.codigo_barras or not producto.nombre:
                raise ValueError("Código de barras y nombre son requeridos")
            
            # Sanitizar datos de entrada
            producto.codigo_barras = self._sanitize_string(producto.codigo_barras)
            producto.nombre = self._sanitize_string(producto.nombre)
            producto.marca = self._sanitize_string(producto.marca)
            
            # Validar formato de código de barras
            if not self.barcode_pattern.match(producto.codigo_barras):
                raise ValueError(f"Formato de código de barras inválido: {producto.codigo_barras}")
            
            # Validar nombre
            if not self.name_pattern.match(producto.nombre):
                raise ValueError(f"Formato de nombre inválido: {producto.nombre}")
            
            # Validar marca
            if not self.brand_pattern.match(producto.marca):
                raise ValueError(f"Formato de marca inválido: {producto.marca}")
            
            # Verificar unicidad de código de barras
            existing = self.get_by_codigo_barras(producto.codigo_barras, user)
            if existing:
                db_logger.warning(f"Intento de duplicar código de barras: {producto.codigo_barras}")
                raise ValueError(f"El código de barras {producto.codigo_barras} ya existe")
            
            # Verificar que la categoría exista
            categoria = self.db.query(models.Categoria).filter(
                and_(
                    models.Categoria.id == producto.categoria_id,
                    models.Categoria.activo == 1
                )
            ).first()
            
            if not categoria:
                raise ValueError(f"La categoría con ID {producto.categoria_id} no existe")
            
            # Validar datos numéricos
            if producto.precio_neto <= 0:
                raise ValueError("El precio neto debe ser mayor a 0")
            
            if producto.cantidad < 0:
                raise ValueError("La cantidad no puede ser negativa")
            
            if producto.porcentaje_ganancia < 0 or producto.porcentaje_ganancia > 1000:
                raise ValueError("El porcentaje de ganancia debe estar entre 0 y 1000")
            
            if producto.iva < 0 or producto.iva > 100:
                raise ValueError("El IVA debe estar entre 0 y 100")
            
            # Crear instancia y calcular precio de venta
            db_producto = models.Producto(**producto.model_dump())
            db_producto.precio_venta = db_producto.calcular_precio_venta()
            
            self.db.add(db_producto)
            self.db.commit()
            self.db.refresh(db_producto)
            
            db_logger.info(f"Producto creado exitosamente: ID={db_producto.id}, Código={db_producto.codigo_barras}")
            return db_producto
            
        except ValueError as e:
            db_logger.error(f"Error de validación en create: {str(e)}")
            raise
        except Exception as e:
            self.db.rollback()
            db_logger.error(f"Error en create: {str(e)}")
            raise

    def update(self, producto_id: int, producto_update: schemas.ProductoUpdate, user: str = "system") -> Optional[models.Producto]:
        """Actualizar producto con validaciones"""
        try:
            params = self._validate_input_parameters(producto_id=producto_id)
            producto_id = params['producto_id']
            
            self._log_query("update", user, producto_id=producto_id, update_data=producto_update.model_dump(exclude_unset=True))
            
            db_producto = self.get_by_id(producto_id, user)
            if not db_producto:
                db_logger.warning(f"Producto no encontrado para actualizar: ID={producto_id}")
                return None
            
            update_data = producto_update.model_dump(exclude_unset=True)
            
            # Sanitizar datos de texto antes de actualizar
            for field in ['codigo_barras', 'nombre', 'marca', 'descripcion']:
                if field in update_data and update_data[field]:
                    update_data[field] = self._sanitize_string(str(update_data[field]))
            
            # Validar código de barras si se está actualizando
            if 'codigo_barras' in update_data:
                if not self.barcode_pattern.match(update_data['codigo_barras']):
                    raise ValueError(f"Formato de código de barras inválido: {update_data['codigo_barras']}")
                
                # Verificar que el nuevo código no exista en otro producto
                existing = self.get_by_codigo_barras(update_data['codigo_barras'], user)
                if existing and existing.id != producto_id:
                    db_logger.warning(f"Intento de duplicar código de barras en update: {update_data['codigo_barras']}")
                    raise ValueError(f"El código de barras {update_data['codigo_barras']} ya existe en otro producto")
            
            # Validar nombre si se está actualizando
            if 'nombre' in update_data and not self.name_pattern.match(update_data['nombre']):
                raise ValueError(f"Formato de nombre inválido: {update_data['nombre']}")
            
            # Validar marca si se está actualizando
            if 'marca' in update_data and not self.brand_pattern.match(update_data['marca']):
                raise ValueError(f"Formato de marca inválido: {update_data['marca']}")
            
            # Validar datos numéricos
            if 'precio_neto' in update_data and update_data['precio_neto'] <= 0:
                raise ValueError("El precio neto debe ser mayor a 0")
            
            if 'cantidad' in update_data and update_data['cantidad'] < 0:
                raise ValueError("La cantidad no puede ser negativa")
            
            if 'porcentaje_ganancia' in update_data and (update_data['porcentaje_ganancia'] < 0 or update_data['porcentaje_ganancia'] > 1000):
                raise ValueError("El porcentaje de ganancia debe estar entre 0 y 1000")
            
            if 'iva' in update_data and (update_data['iva'] < 0 or update_data['iva'] > 100):
                raise ValueError("El IVA debe estar entre 0 y 100")
            
            # Aplicar actualizaciones
            for field, value in update_data.items():
                setattr(db_producto, field, value)
            
            # Recalcular precio de venta si cambió precio_neto, porcentaje_ganancia o iva
            if any(field in update_data for field in ['precio_neto', 'porcentaje_ganancia', 'iva']):
                db_producto.precio_venta = db_producto.calcular_precio_venta()
            
            self.db.commit()
            self.db.refresh(db_producto)
            
            db_logger.info(f"Producto actualizado exitosamente: ID={db_producto.id}")
            return db_producto
            
        except ValueError as e:
            db_logger.error(f"Error de validación en update: {str(e)}")
            raise
        except Exception as e:
            self.db.rollback()
            db_logger.error(f"Error en update: {str(e)}")
            raise

    def partial_update(self, producto_id: int, producto_update: schemas.ProductoUpdate, user: str = "system") -> Optional[models.Producto]:
        """Actualización parcial de producto (alias para update con logging específico)"""
        db_logger.debug(f"Partial update solicitado para producto ID={producto_id}")
        return self.update(producto_id, producto_update, user)

    def delete(self, producto_id: int, user: str = "system") -> bool:
        """Soft delete de producto con validación y logging"""
        try:
            params = self._validate_input_parameters(producto_id=producto_id)
            producto_id = params['producto_id']
            
            self._log_query("delete", user, producto_id=producto_id)
            
            db_producto = self.get_by_id(producto_id, user)
            if not db_producto:
                db_logger.warning(f"Producto no encontrado para eliminar: ID={producto_id}")
                return False
            
            # Soft delete
            db_producto.activo = 0
            self.db.commit()
            
            db_logger.warning(f"Producto eliminado (soft delete): ID={producto_id}, Usuario={user}")
            return True
            
        except ValueError as e:
            db_logger.error(f"Error de validación en delete: {str(e)}")
            raise
        except Exception as e:
            self.db.rollback()
            db_logger.error(f"Error en delete: {str(e)}")
            raise

    def count_all(self) -> int:
        """Contar todos los productos activos"""
        try:
            return self.db.query(models.Producto).filter(
                models.Producto.activo == 1
            ).count()
        except Exception as e:
            db_logger.error(f"Error en count_all: {str(e)}")
            raise

    # Métodos de filtrado con validación
    def filtrar_por_vehiculo(self, filtros: schemas.FiltroVehiculo, skip: int = 0, limit: int = 100, user: str = "system") -> List[models.Producto]:
        """Filtrar productos por características vehiculares con validación"""
        try:
            params = self._validate_input_parameters(skip=skip, limit=limit)
            skip = params['skip']
            limit = params['limit']
            
            self._log_query("filtrar_por_vehiculo", user, filtros=filtros.model_dump(), skip=skip, limit=limit)
            
            query = self.db.query(models.Producto).filter(
                models.Producto.activo == 1
            )
            
            # Validar y aplicar filtros de manera segura
            allowed_fields = ['tipo_vehiculo', 'tipo_aceite', 'tipo_combustible', 'tipo_filtro']
            
            for field in allowed_fields:
                value = getattr(filtros, field)
                if value:
                    # Sanitizar valor del filtro
                    sanitized_value = self._sanitize_string(str(value)).lower()
                    
                    # Validar valores permitidos para cada campo
                    if field == 'tipo_vehiculo' and sanitized_value not in ['auto', 'moto', 'camion', 'bus']:
                        raise ValueError(f"Tipo de vehículo no válido: {sanitized_value}")
                    
                    if field == 'tipo_aceite' and sanitized_value not in ['sintetico', 'mineral', 'semi-sintetico']:
                        raise ValueError(f"Tipo de aceite no válido: {sanitized_value}")
                    
                    if field == 'tipo_combustible' and sanitized_value not in ['gasolina', 'diesel', 'electrico', 'hibrido']:
                        raise ValueError(f"Tipo de combustible no válido: {sanitized_value}")
                    
                    if field == 'tipo_filtro' and sanitized_value not in ['aire', 'aceite', 'combustible', 'polen', 'habitaculo']:
                        raise ValueError(f"Tipo de filtro no válido: {sanitized_value}")
                    
                    query = query.filter(getattr(models.Producto, field) == sanitized_value)
            
            query = query.order_by(models.Producto.id)
            result = query.offset(skip).limit(limit).all()
            
            db_logger.debug(f"Filtrado por vehículo retornó {len(result)} registros")
            return result
            
        except ValueError as e:
            db_logger.error(f"Error de validación en filtrar_por_vehiculo: {str(e)}")
            raise
        except Exception as e:
            db_logger.error(f"Error en filtrar_por_vehiculo: {str(e)}")
            raise

    def filtrar_por_categoria(self, categoria_id: int, skip: int = 0, limit: int = 100, user: str = "system") -> List[models.Producto]:
        """Filtrar productos por categoría con validación"""
        try:
            params = self._validate_input_parameters(categoria_id=categoria_id, skip=skip, limit=limit)
            categoria_id = params['categoria_id']
            skip = params['skip']
            limit = params['limit']
            
            self._log_query("filtrar_por_categoria", user, categoria_id=categoria_id, skip=skip, limit=limit)
            
            # Verificar que la categoría exista
            categoria = self.db.query(models.Categoria).filter(
                and_(
                    models.Categoria.id == categoria_id,
                    models.Categoria.activo == 1
                )
            ).first()
            
            if not categoria:
                db_logger.warning(f"Categoría no encontrada: ID={categoria_id}")
                return []
            
            query = self.db.query(models.Producto).filter(
                and_(
                    models.Producto.categoria_id == categoria_id,
                    models.Producto.activo == 1
                )
            ).order_by(models.Producto.id)
            
            result = query.offset(skip).limit(limit).all()
            db_logger.debug(f"Filtrado por categoría retornó {len(result)} registros")
            return result
            
        except ValueError as e:
            db_logger.error(f"Error de validación en filtrar_por_categoria: {str(e)}")
            raise
        except Exception as e:
            db_logger.error(f"Error en filtrar_por_categoria: {str(e)}")
            raise

    def filtrar_por_distribuidor(self, distribuidor_id: int, skip: int = 0, limit: int = 100, user: str = "system") -> List[models.Producto]:
        """Filtrar productos por distribuidor con validación"""
        try:
            params = self._validate_input_parameters(distribuidor_id=distribuidor_id, skip=skip, limit=limit)
            distribuidor_id = params['distribuidor_id']
            skip = params['skip']
            limit = params['limit']
            
            self._log_query("filtrar_por_distribuidor", user, distribuidor_id=distribuidor_id, skip=skip, limit=limit)
            
            # Verificar que el distribuidor exista
            distribuidor = self.db.query(models.Distribuidor).filter(
                and_(
                    models.Distribuidor.id == distribuidor_id,
                    models.Distribuidor.activo == 1
                )
            ).first()
            
            if not distribuidor:
                db_logger.warning(f"Distribuidor no encontrado: ID={distribuidor_id}")
                return []
            
            query = self.db.query(models.Producto).filter(
                and_(
                    models.Producto.distribuidor_id == distribuidor_id,
                    models.Producto.activo == 1
                )
            ).order_by(models.Producto.id)
            
            result = query.offset(skip).limit(limit).all()
            db_logger.debug(f"Filtrado por distribuidor retornó {len(result)} registros")
            return result
            
        except ValueError as e:
            db_logger.error(f"Error de validación en filtrar_por_distribuidor: {str(e)}")
            raise
        except Exception as e:
            db_logger.error(f"Error en filtrar_por_distribuidor: {str(e)}")
            raise

    # Nuevos métodos para auditoría y monitoreo
    def get_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de productos para monitoreo"""
        try:
            stats = {
                "total_productos": self.count_all(),
                "por_categoria": {},
                "por_tipo_vehiculo": {},
                "por_tipo_filtro": {}
            }
            
            # Productos por categoría
            categorias = self.db.query(
                models.Categoria.nombre,
                func.count(models.Producto.id)
            ).join(
                models.Producto,
                models.Producto.categoria_id == models.Categoria.id
            ).filter(
                models.Producto.activo == 1
            ).group_by(models.Categoria.nombre).all()
            
            stats["por_categoria"] = dict(categorias)
            
            # Productos por tipo de vehículo (solo para productos con ese campo)
            tipos_vehiculo = self.db.query(
                models.Producto.tipo_vehiculo,
                func.count(models.Producto.id)
            ).filter(
                and_(
                    models.Producto.activo == 1,
                    models.Producto.tipo_vehiculo.isnot(None)
                )
            ).group_by(models.Producto.tipo_vehiculo).all()
            
            stats["por_tipo_vehiculo"] = dict(tipos_vehiculo)
            
            # Productos por tipo de filtro
            tipos_filtro = self.db.query(
                models.Producto.tipo_filtro,
                func.count(models.Producto.id)
            ).filter(
                and_(
                    models.Producto.activo == 1,
                    models.Producto.tipo_filtro.isnot(None)
                )
            ).group_by(models.Producto.tipo_filtro).all()
            
            stats["por_tipo_filtro"] = dict(tipos_filtro)
            
            return stats
            
        except Exception as e:
            db_logger.error(f"Error obteniendo estadísticas: {str(e)}")
            return {}