from enum import Enum
from typing import Dict, List

class TipoVehiculo(str, Enum):
    AUTO = "auto"
    MOTO = "moto"
    CAMION = "camion"
    BUS = "bus"

class TipoAceite(str, Enum):
    SINTETICO = "sintetico"
    MINERAL = "mineral"
    SEMI_SINTETICO = "semi-sintetico"

class TipoCombustible(str, Enum):
    GASOLINA = "gasolina"
    DIESEL = "diesel"
    ELECTRICO = "electrico"
    HIBRIDO = "hibrido"

class TipoFiltro(str, Enum):
    AIRE = "aire"
    ACEITE = "aceite"
    COMBUSTIBLE = "combustible"
    POLEN = "polen"

class VehicleFilter:
    @staticmethod
    def get_available_filters() -> Dict[str, List[str]]:
        return {
            "tipo_vehiculo": [item.value for item in TipoVehiculo],
            "tipo_aceite": [item.value for item in TipoAceite],
            "tipo_combustible": [item.value for item in TipoCombustible],
            "tipo_filtro": [item.value for item in TipoFiltro]
        }
    
    @staticmethod
    def validate_filter_value(filter_type: str, value: str) -> bool:
        filter_map = {
            "tipo_vehiculo": TipoVehiculo,
            "tipo_aceite": TipoAceite,
            "tipo_combustible": TipoCombustible,
            "tipo_filtro": TipoFiltro
        }
        
        if filter_type in filter_map:
            enum_class = filter_map[filter_type]
            return value in [item.value for item in enum_class]
        return False