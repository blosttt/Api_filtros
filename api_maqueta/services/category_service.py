import logging
import re
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional, Dict, Any
import models
import schemas

# Logger para operaciones de categorías
category_logger = logging.getLogger("category")

class CategoryService:
    def __init__(self, db: Session):
        self.db = db
        # Patrones regex para validación
        self.name_pattern = re.compile(r'^[A-Za-z0-9\s\-_.,;:áéíóúÁÉÍÓÚñÑ]{1,50}$')
        self.tipo_pattern = re.compile(r'^[a-z_]{1,20}$')  # Solo minúsculas y guiones bajos
        self.description_pattern = re.compile(r'^[A-Za-z0-9\s\-_.,;:áéíóúÁÉÍÓÚñÑ()]{0,500}$')

    def _validate_input_parameters(self, **kwargs) -> Dict[str, Any]:
        """Valida y sanitiza parámetros de entrada"""
        validated = {}
        
        for key, value in kwargs.items():
            if value is None:
                validated[key] = None
                continue
                
            # Validaciones específicas por tipo de parámetro
            if key in ['categoria_id'] and value < 1:
                raise ValueError(f"ID inválido: {key}={value}. Debe ser mayor a 0")
            
            if key == 'tipo' and value:
                if not isinstance(value, str):
                    raise ValueError("El tipo debe ser una cadena de texto")
                value = value.strip().lower()
                if not self.tipo_pattern.match(value):
                    raise ValueError(f"Tipo con formato inválido: {value}")
                # Validar tipos permitidos
                allowed_types = ['vehiculo', 'general', 'repuesto', 'lubricante', 'filtro', 'aceite', 'accesorio']
                if value not in allowed_types:
                    raise ValueError(f"Tipo no permitido. Valores permitidos: {', '.join(allowed_types)}")
            
            if key == 'nombre' and value:
                if not isinstance(value, str):
                    raise ValueError("El nombre debe ser una cadena de texto")
                value = value.strip()
                if not self.name_pattern.match(value):
                    raise ValueError(f"Nombre con formato inválido: {value}")
            
            if key == 'descripcion' and value:
                if not isinstance(value, str):
                    raise ValueError("La descripción debe ser una cadena de texto")
                value = value.strip()
                if len(value) > 500:
                    raise ValueError("La descripción no puede exceder 500 caracteres")
                if not self.description_pattern.match(value):
                    raise ValueError(f"Descripción con formato inválido: {value}")
            
            validated[key] = value
        
        return validated

    def _sanitize_string(self, value: str) -> str:
        """Sanitiza cadenas para prevenir inyecciones"""
        if not value:
            return value
        
        # Remover caracteres peligrosos
        value = value.strip()
        value = re.sub(r'[\x00-\x1F\x7F]', '', value)  # Control characters
        value = re.sub(r'[\'"\\;]', '', value)  # Caracteres SQL peligrosos
        
        return value

    def _log_operation(self, operation: str, user: str = "system", **kwargs):
        """Log de operaciones para auditoría"""
        # Ocultar información sensible en logs
        safe_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str) and len(value) > 50:
                safe_kwargs[key] = value[:50] + "..."
            elif 'password' in key.lower() or 'secret' in key.lower():
                safe_kwargs[key] = "***REDACTED***"
            else:
                safe_kwargs[key] = value
        
        category_logger.info(
            f"Category Operation: {operation}, User: {user}, "
            f"Params: {safe_kwargs}"
        )

    def get_all(self, user: str = "system") -> List[models.Categoria]:
        """Obtener todas las categorías activas"""
        try:
            self._log_operation("get_all", user)
            
            query = self.db.query(models.Categoria).filter(
                models.Categoria.activo == 1
            ).order_by(models.Categoria.nombre)
            
            result = query.all()
            category_logger.debug(f"Consulta get_all retornó {len(result)} categorías")
            return result
            
        except Exception as e:
            category_logger.error(f"Error en get_all: {str(e)}")
            raise

    def get_by_id(self, categoria_id: int, user: str = "system") -> Optional[models.Categoria]:
        """Obtener categoría por ID con validación"""
        try:
            params = self._validate_input_parameters(categoria_id=categoria_id)
            categoria_id = params['categoria_id']
            
            self._log_operation("get_by_id", user, categoria_id=categoria_id)
            
            result = self.db.query(models.Categoria).filter(
                and_(
                    models.Categoria.id == categoria_id,
                    models.Categoria.activo == 1
                )
            ).first()
            
            if not result:
                category_logger.warning(f"Categoría no encontrada: ID={categoria_id}")
            
            return result
            
        except ValueError as e:
            category_logger.error(f"Error de validación en get_by_id: {str(e)}")
            raise
        except Exception as e:
            category_logger.error(f"Error en get_by_id: {str(e)}")
            raise

    def get_by_tipo(self, tipo: str, user: str = "system") -> List[models.Categoria]:
        """Obtener categorías por tipo con validación"""
        try:
            params = self._validate_input_parameters(tipo=tipo)
            tipo = params['tipo']
            
            self._log_operation("get_by_tipo", user, tipo=tipo)
            
            # Sanitizar tipo
            tipo = self._sanitize_string(tipo)
            
            query = self.db.query(models.Categoria).filter(
                and_(
                    models.Categoria.tipo == tipo,
                    models.Categoria.activo == 1
                )
            ).order_by(models.Categoria.nombre)
            
            result = query.all()
            category_logger.debug(f"Consulta get_by_tipo retornó {len(result)} categorías para tipo '{tipo}'")
            return result
            
        except ValueError as e:
            category_logger.error(f"Error de validación en get_by_tipo: {str(e)}")
            raise
        except Exception as e:
            category_logger.error(f"Error en get_by_tipo: {str(e)}")
            raise

    def create(self, categoria: schemas.CategoriaCreate, user: str = "system") -> models.Categoria:
        """Crear nueva categoría con validaciones extensivas"""
        try:
            self._log_operation("create", user, categoria_data=categoria.model_dump())
            
            # Validar datos requeridos
            if not categoria.nombre:
                raise ValueError("El nombre de la categoría es requerido")
            
            # Sanitizar datos de entrada
            categoria.nombre = self._sanitize_string(categoria.nombre)
            categoria.descripcion = self._sanitize_string(categoria.descripcion) if categoria.descripcion else None
            categoria.tipo = self._sanitize_string(categoria.tipo) if categoria.tipo else "general"
            
            # Validar formato del nombre
            if not self.name_pattern.match(categoria.nombre):
                raise ValueError(f"Formato de nombre inválido: {categoria.nombre}")
            
            # Validar longitud máxima
            if len(categoria.nombre) > 50:
                raise ValueError("El nombre no puede exceder 50 caracteres")
            
            # Validar tipo
            if categoria.tipo and not self.tipo_pattern.match(categoria.tipo):
                raise ValueError(f"Formato de tipo inválido: {categoria.tipo}")
            
            # Validar tipos permitidos
            allowed_types = ['vehiculo', 'general', 'repuesto', 'lubricante', 'filtro', 'aceite', 'accesorio']
            if categoria.tipo.lower() not in allowed_types:
                raise ValueError(f"Tipo no permitido. Valores permitidos: {', '.join(allowed_types)}")
            
            # Validar descripción
            if categoria.descripcion and len(categoria.descripcion) > 500:
                raise ValueError("La descripción no puede exceder 500 caracteres")
            
            # Verificar unicidad del nombre (insensible a mayúsculas)
            existing = self.db.query(models.Categoria).filter(
                and_(
                    func.lower(models.Categoria.nombre) == categoria.nombre.lower(),
                    models.Categoria.activo == 1
                )
            ).first()
            
            if existing:
                category_logger.warning(f"Intento de duplicar categoría: {categoria.nombre}")
                raise ValueError(f"La categoría '{categoria.nombre}' ya existe")
            
            # Crear instancia
            db_categoria = models.Categoria(**categoria.model_dump())
            
            self.db.add(db_categoria)
            self.db.commit()
            self.db.refresh(db_categoria)
            
            category_logger.info(f"Categoría creada exitosamente: ID={db_categoria.id}, Nombre={db_categoria.nombre}")
            return db_categoria
            
        except ValueError as e:
            category_logger.error(f"Error de validación en create: {str(e)}")
            raise
        except Exception as e:
            self.db.rollback()
            category_logger.error(f"Error en create: {str(e)}")
            raise

    def update(self, categoria_id: int, categoria_update: schemas.CategoriaCreate, user: str = "system") -> Optional[models.Categoria]:
        """Actualizar categoría existente con validaciones"""
        try:
            params = self._validate_input_parameters(categoria_id=categoria_id)
            categoria_id = params['categoria_id']
            
            self._log_operation("update", user, categoria_id=categoria_id, update_data=categoria_update.model_dump())
            
            # Obtener categoría existente
            db_categoria = self.get_by_id(categoria_id, user)
            if not db_categoria:
                category_logger.warning(f"Categoría no encontrada para actualizar: ID={categoria_id}")
                return None
            
            # Sanitizar datos de entrada
            categoria_update.nombre = self._sanitize_string(categoria_update.nombre)
            categoria_update.descripcion = self._sanitize_string(categoria_update.descripcion) if categoria_update.descripcion else None
            categoria_update.tipo = self._sanitize_string(categoria_update.tipo) if categoria_update.tipo else db_categoria.tipo
            
            # Validar formato del nombre
            if not self.name_pattern.match(categoria_update.nombre):
                raise ValueError(f"Formato de nombre inválido: {categoria_update.nombre}")
            
            # Validar tipo
            if categoria_update.tipo and not self.tipo_pattern.match(categoria_update.tipo):
                raise ValueError(f"Formato de tipo inválido: {categoria_update.tipo}")
            
            # Validar tipos permitidos
            allowed_types = ['vehiculo', 'general', 'repuesto', 'lubricante', 'filtro', 'aceite', 'accesorio']
            if categoria_update.tipo.lower() not in allowed_types:
                raise ValueError(f"Tipo no permitido. Valores permitidos: {', '.join(allowed_types)}")
            
            # Verificar unicidad del nombre (excepto para esta misma categoría)
            existing = self.db.query(models.Categoria).filter(
                and_(
                    func.lower(models.Categoria.nombre) == categoria_update.nombre.lower(),
                    models.Categoria.id != categoria_id,
                    models.Categoria.activo == 1
                )
            ).first()
            
            if existing:
                category_logger.warning(f"Intento de duplicar categoría en update: {categoria_update.nombre}")
                raise ValueError(f"La categoría '{categoria_update.nombre}' ya existe en otra categoría")
            
            # Actualizar campos
            db_categoria.nombre = categoria_update.nombre
            db_categoria.descripcion = categoria_update.descripcion
            db_categoria.tipo = categoria_update.tipo
            
            self.db.commit()
            self.db.refresh(db_categoria)
            
            category_logger.info(f"Categoría actualizada exitosamente: ID={db_categoria.id}, Nombre={db_categoria.nombre}")
            return db_categoria
            
        except ValueError as e:
            category_logger.error(f"Error de validación en update: {str(e)}")
            raise
        except Exception as e:
            self.db.rollback()
            category_logger.error(f"Error en update: {str(e)}")
            raise

    def delete(self, categoria_id: int, user: str = "system") -> bool:
        """Soft delete de categoría con validaciones"""
        try:
            params = self._validate_input_parameters(categoria_id=categoria_id)
            categoria_id = params['categoria_id']
            
            self._log_operation("delete", user, categoria_id=categoria_id)
            
            # Obtener categoría
            db_categoria = self.get_by_id(categoria_id, user)
            if not db_categoria:
                category_logger.warning(f"Categoría no encontrada para eliminar: ID={categoria_id}")
                return False
            
            # Verificar si hay productos asociados
            product_count = self.db.query(models.Producto).filter(
                and_(
                    models.Producto.categoria_id == categoria_id,
                    models.Producto.activo == 1
                )
            ).count()
            
            if product_count > 0:
                category_logger.warning(
                    f"No se puede eliminar categoría {categoria_id} porque tiene {product_count} productos asociados"
                )
                raise ValueError(f"No se puede eliminar la categoría porque tiene {product_count} producto(s) asociado(s). "
                               "Reasigna los productos primero.")
            
            # Soft delete
            db_categoria.activo = 0
            self.db.commit()
            
            category_logger.warning(f"Categoría eliminada (soft delete): ID={categoria_id}, Nombre={db_categoria.nombre}, Usuario={user}")
            return True
            
        except ValueError as e:
            category_logger.error(f"Error de validación en delete: {str(e)}")
            raise
        except Exception as e:
            self.db.rollback()
            category_logger.error(f"Error en delete: {str(e)}")
            raise

    def get_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de categorías"""
        try:
            stats = {
                "total_categorias": 0,
                "categorias_por_tipo": {},
                "productos_por_categoria": {},
                "categorias_mas_utilizadas": []
            }
            
            # Total de categorías activas
            stats["total_categorias"] = self.db.query(models.Categoria).filter(
                models.Categoria.activo == 1
            ).count()
            
            # Categorías por tipo
            tipos = self.db.query(
                models.Categoria.tipo,
                func.count(models.Categoria.id)
            ).filter(
                models.Categoria.activo == 1
            ).group_by(models.Categoria.tipo).all()
            
            stats["categorias_por_tipo"] = dict(tipos)
            
            # Productos por categoría (top 10)
            productos_por_categoria = self.db.query(
                models.Categoria.nombre,
                func.count(models.Producto.id)
            ).join(
                models.Producto,
                models.Producto.categoria_id == models.Categoria.id
            ).filter(
                and_(
                    models.Categoria.activo == 1,
                    models.Producto.activo == 1
                )
            ).group_by(models.Categoria.nombre).order_by(func.count(models.Producto.id).desc()).limit(10).all()
            
            stats["productos_por_categoria"] = dict(productos_por_categoria)
            
            # Categorías más utilizadas (con productos)
            categorias_con_productos = self.db.query(
                models.Categoria.nombre,
                func.count(models.Producto.id).label('product_count')
            ).join(
                models.Producto,
                models.Producto.categoria_id == models.Categoria.id
            ).filter(
                and_(
                    models.Categoria.activo == 1,
                    models.Producto.activo == 1
                )
            ).group_by(models.Categoria.nombre).order_by(func.count(models.Producto.id).desc()).limit(5).all()
            
            stats["categorias_mas_utilizadas"] = [
                {"nombre": nombre, "productos": count}
                for nombre, count in categorias_con_productos
            ]
            
            return stats
            
        except Exception as e:
            category_logger.error(f"Error obteniendo estadísticas: {str(e)}")
            return {}

    def search(self, query: str, limit: int = 20, user: str = "system") -> List[models.Categoria]:
        """Búsqueda segura de categorías"""
        try:
            if not query or len(query.strip()) < 2:
                raise ValueError("La consulta de búsqueda debe tener al menos 2 caracteres")
            
            # Sanitizar y validar query
            query = self._sanitize_string(query.strip())
            if len(query) > 100:
                raise ValueError("La consulta no puede exceder 100 caracteres")
            
            # Validar limit
            if limit < 1 or limit > 100:
                limit = 20
            
            self._log_operation("search", user, query=query, limit=limit)
            
            # Búsqueda segura usando like con parámetros
            # CORREGIR:
            result = self.db.query(models.Categoria).filter(
                and_(
                    models.Categoria.activo == 1,
                    or_(
                        models.Categoria.nombre.ilike(search_query),  # Cambiar llike por ilike
                        models.Categoria.descripcion.ilike(search_query) if models.Categoria.descripcion else False  # Cambiar llike por ilike
                    )
                )
            ).order_by(models.Categoria.nombre).limit(limit).all()
            
            category_logger.debug(f"Búsqueda retornó {len(result)} categorías para query: '{query}'")
            return result
            
        except ValueError as e:
            category_logger.error(f"Error de validación en search: {str(e)}")
            raise
        except Exception as e:
            category_logger.error(f"Error en search: {str(e)}")
            raise