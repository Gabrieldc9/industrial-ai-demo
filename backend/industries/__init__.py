from .base import IndustryPlugin, EquipmentDef, SensorDef, FaultMode
from .oil_gas import OIL_GAS_BATERIA
from .generic import GENERIC_MANUFACTURING

INDUSTRIES: dict[str, IndustryPlugin] = {
    OIL_GAS_BATERIA.industry_id:       OIL_GAS_BATERIA,
    GENERIC_MANUFACTURING.industry_id:  GENERIC_MANUFACTURING,
}

DEFAULT_INDUSTRY = OIL_GAS_BATERIA
