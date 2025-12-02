from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Dict
import models
import schemas

class ProductService:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100) -> List[models.Filtros]:
        return self.db.query(models.Filtros).offset(skip).limit(limit).all()

    def get_by_id(self, filtro_id: int) -> Optional[models.Filtros]:
        return self.db.query(models.Filtros).filter(
            models.Filtros.id_filtro == filtro_id
        ).first()

    def get_by_codigo_producto(self, codigo_producto: str) -> Optional[models.Filtros]:
        return self.db.query(models.Filtros).filter(
            models.Filtros.codigo_producto == codigo_producto
        ).first()

    def create(self, filtro: schemas.FiltroCreate) -> models.Filtros:
        # Verificar si el código de producto ya existe
        if self.get_by_codigo_producto(filtro.codigo_producto):
            raise ValueError(f"El código de producto {filtro.codigo_producto} ya existe")
        
        # Crear instancia
        db_filtro = models.Filtros(**filtro.model_dump())
        
        self.db.add(db_filtro)
        self.db.commit()
        self.db.refresh(db_filtro)
        return db_filtro

    def update(self, filtro_id: int, filtro_update: schemas.FiltroUpdate) -> Optional[models.Filtros]:
        db_filtro = self.get_by_id(filtro_id)
        if not db_filtro:
            return None
        
        update_data = filtro_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_filtro, field, value)
        
        self.db.commit()
        self.db.refresh(db_filtro)
        return db_filtro

    def partial_update(self, filtro_id: int, filtro_update: schemas.FiltroUpdate) -> Optional[models.Filtros]:
        return self.update(filtro_id, filtro_update)

    def delete(self, filtro_id: int) -> bool:
        db_filtro = self.get_by_id(filtro_id)
        if not db_filtro:
            return False
        
        self.db.delete(db_filtro)
        self.db.commit()
        return True

    def count_all(self) -> int:
        return self.db.query(models.Filtros).count()


    def filtrar_por_categoria(self, categoria_id: int, skip: int = 0, limit: int = 100) -> List[models.Filtros]:
        return self.db.query(models.Filtros).filter(
            models.Filtros.id_categoria == categoria_id
        ).offset(skip).limit(limit).all()

    def filtrar_por_distribuidor(self, distribuidor_id: int, skip: int = 0, limit: int = 100) -> List[models.Filtros]:
        return self.db.query(models.Filtros).filter(
            models.Filtros.id_distribuidor == distribuidor_id
        ).offset(skip).limit(limit).all()