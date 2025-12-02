import logging
import re
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

# Logger para operaciones de filtros
filter_logger = logging.getLogger("filters")

class TipoVehiculo(str, Enum):
    AUTO = "auto"
    MOTO = "moto"
    CAMION = "camion"
    BUS = "bus"
    MAQUINARIA = "maquinaria"
    AGRICOLA = "agricola"

class TipoAceite(str, Enum):
    SINTETICO = "sintetico"
    MINERAL = "mineral"
    SEMI_SINTETICO = "semi-sintetico"
    TRANSMISION = "transmision"
    HIDRAULICO = "hidraulico"

class TipoCombustible(str, Enum):
    GASOLINA = "gasolina"
    DIESEL = "diesel"
    ELECTRICO = "electrico"
    HIBRIDO = "hibrido"
    GAS = "gas"
    BIOCOMBUSTIBLE = "biocombustible"

class TipoFiltro(str, Enum):
    AIRE = "aire"
    ACEITE = "aceite"
    COMBUSTIBLE = "combustible"
    POLEN = "polen"
    HABITACULO = "habitaculo"
    HIDRAULICO = "hidraulico"
    TRANSMISION = "transmision"
    AGUA = "agua"

@dataclass
class FilterCompatibility:
    """Define compatibilidades entre filtros"""
    tipo_vehiculo_compatible: List[str]
    tipo_aceite_compatible: List[str]
    tipo_combustible_compatible: List[str]
    tipo_filtro_compatible: List[str]

class VehicleFilter:
    # Mapeo de compatibilidades (ejemplo simplificado)
    COMPATIBILITY_MAP = {
        "auto": FilterCompatibility(
            tipo_vehiculo_compatible=["auto", "moto"],
            tipo_aceite_compatible=["sintetico", "mineral", "semi-sintetico"],
            tipo_combustible_compatible=["gasolina", "diesel", "hibrido", "electrico"],
            tipo_filtro_compatible=["aire", "aceite", "combustible", "polen", "habitaculo"]
        ),
        "moto": FilterCompatibility(
            tipo_vehiculo_compatible=["moto"],
            tipo_aceite_compatible=["sintetico", "mineral", "semi-sintetico"],
            tipo_combustible_compatible=["gasolina"],
            tipo_filtro_compatible=["aire", "aceite", "combustible"]
        ),
        "camion": FilterCompatibility(
            tipo_vehiculo_compatible=["camion", "bus", "maquinaria"],
            tipo_aceite_compatible=["mineral", "semi-sintetico", "hidraulico"],
            tipo_combustible_compatible=["diesel", "gas"],
            tipo_filtro_compatible=["aire", "aceite", "combustible", "hidraulico"]
        )
    }
    
    @staticmethod
    def _sanitize_input(value: str) -> str:
        """Sanitiza entrada para prevenir inyecciones"""
        if not value or not isinstance(value, str):
            return ""
        
        # Remover caracteres peligrosos
        value = value.strip().lower()
        value = re.sub(r'[\x00-\x1F\x7F]', '', value)  # Control characters
        value = re.sub(r'[\'"\\;<>]', '', value)  # Caracteres peligrosos
        
        # Validar que solo contenga caracteres permitidos
        if not re.match(r'^[a-z0-9\-_]+$', value):
            return ""
        
        return value
    
    @staticmethod
    def get_available_filters() -> Dict[str, List[str]]:
        """Obtiene todos los filtros disponibles de manera segura"""
        filter_logger.info("Solicitud de filtros disponibles")
        
        return {
            "tipo_vehiculo": [item.value for item in TipoVehiculo],
            "tipo_aceite": [item.value for item in TipoAceite],
            "tipo_combustible": [item.value for item in TipoCombustible],
            "tipo_filtro": [item.value for item in TipoFiltro]
        }
    
    @staticmethod
    def validate_filter_value(filter_type: str, value: str) -> Tuple[bool, Optional[str]]:
        """
        Valida un valor de filtro de manera segura
        Retorna: (es_valido, mensaje_error)
        """
        try:
            # Sanitizar entradas
            filter_type = VehicleFilter._sanitize_input(filter_type)
            value = VehicleFilter._sanitize_input(value)
            
            if not filter_type or not value:
                return False, "Tipo de filtro o valor vacío"
            
            # Mapeo seguro de tipos de filtro
            filter_map = {
                "tipo_vehiculo": TipoVehiculo,
                "tipo_aceite": TipoAceite,
                "tipo_combustible": TipoCombustible,
                "tipo_filtro": TipoFiltro
            }
            
            if filter_type not in filter_map:
                filter_logger.warning(f"Tipo de filtro desconocido: {filter_type}")
                return False, f"Tipo de filtro no válido: {filter_type}"
            
            enum_class = filter_map[filter_type]
            valid_values = [item.value for item in enum_class]
            
            if value not in valid_values:
                filter_logger.warning(f"Valor de filtro no válido: {filter_type}={value}")
                return False, f"Valor '{value}' no válido para {filter_type}"
            
            filter_logger.debug(f"Validación exitosa: {filter_type}={value}")
            return True, None
            
        except Exception as e:
            filter_logger.error(f"Error en validación de filtro: {str(e)}")
            return False, "Error interno en validación de filtro"
    
    @staticmethod
    def validate_filter_combo(filters: Dict[str, str]) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Valida combinaciones de filtros para compatibilidad
        Retorna: (es_valido, mensaje_error, filtros_sanitizados)
        """
        try:
            if not filters:
                return True, None, {}
            
            sanitized_filters = {}
            
            # Sanitizar todos los filtros
            for filter_type, value in filters.items():
                sanitized_type = VehicleFilter._sanitize_input(filter_type)
                sanitized_value = VehicleFilter._sanitize_input(value)
                
                if not sanitized_type or not sanitized_value:
                    continue
                
                # Validar cada filtro individualmente
                is_valid, error_msg = VehicleFilter.validate_filter_value(sanitized_type, sanitized_value)
                if not is_valid:
                    filter_logger.warning(f"Filtro inválido en combo: {sanitized_type}={sanitized_value} - {error_msg}")
                    return False, f"Filtro inválido: {error_msg}", None
                
                sanitized_filters[sanitized_type] = sanitized_value
            
            # Validar compatibilidad entre filtros
            if len(sanitized_filters) > 1:
                compatibility_error = VehicleFilter._check_compatibility(sanitized_filters)
                if compatibility_error:
                    filter_logger.warning(f"Incompatibilidad en filtros: {compatibility_error}")
                    return False, compatibility_error, None
            
            filter_logger.info(f"Combinación de filtros validada: {sanitized_filters}")
            return True, None, sanitized_filters
            
        except Exception as e:
            filter_logger.error(f"Error en validación de combo de filtros: {str(e)}")
            return False, "Error interno en validación de filtros", None
    
    @staticmethod
    def _check_compatibility(filters: Dict[str, str]) -> Optional[str]:
        """Verifica compatibilidad entre diferentes filtros"""
        
        # Reglas de compatibilidad básicas
        rules = [
            # Un filtro de aceite sintético no es compatible con vehículos diesel viejos
            lambda f: (
                f.get("tipo_aceite") == "sintetico" and 
                f.get("tipo_combustible") == "diesel" and
                f.get("tipo_vehiculo") in ["camion", "bus"]
            ),
            # Filtros de habitáculo solo para autos
            lambda f: (
                f.get("tipo_filtro") == "habitaculo" and 
                f.get("tipo_vehiculo") not in ["auto", "bus", None]
            ),
            # Vehículos eléctricos no usan filtros de combustible
            lambda f: (
                f.get("tipo_combustible") == "electrico" and 
                f.get("tipo_filtro") == "combustible"
            ),
            # Motos no usan filtros de polen/habitáculo
            lambda f: (
                f.get("tipo_vehiculo") == "moto" and 
                f.get("tipo_filtro") in ["polen", "habitaculo"]
            )
        ]
        
        for rule in rules:
            if rule(filters):
                return "Combinación de filtros incompatible"
        
        return None
    
    @staticmethod
    def get_recommended_filters(vehicle_type: str) -> Dict[str, List[str]]:
        """
        Obtiene filtros recomendados basados en el tipo de vehículo
        """
        vehicle_type = VehicleFilter._sanitize_input(vehicle_type)
        
        if not vehicle_type:
            return {}
        
        # Validar tipo de vehículo
        is_valid, error_msg = VehicleFilter.validate_filter_value("tipo_vehiculo", vehicle_type)
        if not is_valid:
            filter_logger.warning(f"Tipo de vehículo no válido para recomendaciones: {vehicle_type}")
            return {}
        
        # Recomendaciones basadas en tipo de vehículo
        recommendations = {
            "auto": {
                "tipo_aceite": ["sintetico", "semi-sintetico"],
                "tipo_combustible": ["gasolina", "diesel", "hibrido"],
                "tipo_filtro": ["aire", "aceite", "combustible", "polen", "habitaculo"]
            },
            "moto": {
                "tipo_aceite": ["sintetico", "semi-sintetico"],
                "tipo_combustible": ["gasolina"],
                "tipo_filtro": ["aire", "aceite", "combustible"]
            },
            "camion": {
                "tipo_aceite": ["mineral", "semi-sintetico"],
                "tipo_combustible": ["diesel", "gas"],
                "tipo_filtro": ["aire", "aceite", "combustible", "hidraulico"]
            },
            "bus": {
                "tipo_aceite": ["mineral", "semi-sintetico"],
                "tipo_combustible": ["diesel"],
                "tipo_filtro": ["aire", "aceite", "combustible"]
            }
        }
        
        if vehicle_type in recommendations:
            filter_logger.info(f"Recomendaciones generadas para: {vehicle_type}")
            return recommendations[vehicle_type]
        
        return {}
    
    @staticmethod
    def get_filter_descriptions() -> Dict[str, Dict[str, str]]:
        """
        Obtiene descripciones de cada filtro para documentación
        """
        descriptions = {
            "tipo_vehiculo": {
                "auto": "Automóvil de pasajeros",
                "moto": "Motocicleta o scooter",
                "camion": "Vehículo de carga pesada",
                "bus": "Autobús o transporte público",
                "maquinaria": "Maquinaria pesada",
                "agricola": "Vehículo agrícola"
            },
            "tipo_aceite": {
                "sintetico": "Aceite sintético de alto rendimiento",
                "mineral": "Aceite mineral convencional",
                "semi-sintetico": "Aceite semi-sintético",
                "transmision": "Aceite para transmisión",
                "hidraulico": "Aceite hidráulico"
            },
            "tipo_combustible": {
                "gasolina": "Motores a gasolina",
                "diesel": "Motores diésel",
                "electrico": "Vehículos eléctricos",
                "hibrido": "Vehículos híbridos",
                "gas": "Vehículos a gas natural",
                "biocombustible": "Biocombustibles"
            },
            "tipo_filtro": {
                "aire": "Filtro de aire del motor",
                "aceite": "Filtro de aceite",
                "combustible": "Filtro de combustible",
                "polen": "Filtro de polen/habitáculo",
                "habitaculo": "Filtro de aire del habitáculo",
                "hidraulico": "Filtro hidráulico",
                "transmision": "Filtro de transmisión",
                "agua": "Filtro de agua/combustible"
            }
        }
        
        return descriptions
    
    @staticmethod
    def audit_filter_usage(filters: Dict[str, str], user_ip: str = "unknown") -> None:
        """
        Registra el uso de filtros para auditoría
        """
        try:
            sanitized_filters = {}
            for key, value in filters.items():
                sanitized_key = VehicleFilter._sanitize_input(key)[:20]  # Limitar longitud
                sanitized_value = VehicleFilter._sanitize_input(value)[:50]
                if sanitized_key and sanitized_value:
                    sanitized_filters[sanitized_key] = sanitized_value
            
            filter_logger.info(
                f"Auditoría de filtros - IP: {user_ip[:15]}, "
                f"Filtros: {sanitized_filters}"
            )
            
        except Exception as e:
            filter_logger.error(f"Error en auditoría de filtros: {str(e)}")

# Función helper para validación rápida
def validate_and_sanitize_filters(**kwargs) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Función de conveniencia para validar y sanitizar filtros
    """
    return VehicleFilter.validate_filter_combo(kwargs)