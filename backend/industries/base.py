"""
Dataclasses base para el sistema de industrias pluggable.

Cada industria es un IndustryPlugin que define:
  - Equipos (con sensores, modos de falla y valores nominales propios)
  - KPIs específicos calculados en tiempo real
  - Condiciones iniciales para demos interesantes desde el minuto 0
"""
from dataclasses import dataclass, field
from typing import Optional, Callable


@dataclass
class SensorDef:
    """
    Definición completa de un sensor en un equipo.

    Dirección de alerta se infiere de los umbrales:
      warning > critical  →  bajo es malo (presión, caudal, eficiencia)
      warning < critical  →  alto es malo  (temperatura, vibración, H2S)
    """
    display_name: str     # Nombre visible en UI ("Temperatura", "Caudal", etc.)
    unit: str             # Unidad de medida ("°C", "bar", "m³/d", "%", etc.)
    nominal: float        # Valor de operación normal (saludable, 100%)
    warning: float        # Umbral de advertencia
    critical: float       # Umbral de falla crítica
    noise_pct: float = 0.01   # Ruido gaussiano como % del valor nominal

    @property
    def is_low_sensor(self) -> bool:
        """True si alertar cuando el valor cae (warning > critical)."""
        return self.warning > self.critical

    @property
    def critical_dist(self) -> float:
        """Distancia entre nominal y umbral crítico."""
        return abs(self.critical - self.nominal)


@dataclass
class FaultMode:
    """
    Modo de falla que puede afectar a un equipo.

    sensor_effects: sensor_key → desplazamiento en unidades del sensor al llegar a 0% health.
      Positivo  → empuja el sensor HACIA ARRIBA (temperatura sube, presión sube)
      Negativo  → empuja el sensor HACIA ABAJO  (caudal cae, eficiencia cae)

    El efecto real se escala por (1 - health_factor):
      effect = sensor_effects[sensor] × (1 - health_factor)
    """
    mode_id: str
    display_name: str
    sensor_effects: dict          # sensor_key → float (en unidades del sensor)
    degradation_multiplier: float = 5.0


@dataclass
class EquipmentDef:
    """Definición completa de un equipo dentro de una industria."""
    eq_id: str
    name: str
    eq_type: str
    icon: str
    area: str                     # Área de la planta ("Pozos", "Separación", etc.)
    sensors: dict                 # sensor_key → SensorDef
    fault_modes: list             # list[FaultMode]
    initial_health_range: tuple = (75, 100)
    base_degradation: tuple = (0.002, 0.008)   # (min, max) % health / tick
    criticality: str = "medium"   # low | medium | high | critical


@dataclass
class IndustryPlugin:
    """Definición completa de una industria para el simulador."""
    industry_id: str
    display_name: str
    icon: str
    description: str
    site_name: str
    equipment: list               # list[EquipmentDef]
    # Condiciones iniciales para que la demo arranque interesante
    initial_conditions: dict = field(default_factory=dict)
    # Función que calcula KPIs específicos de industria
    kpi_computer: Optional[Callable] = None

    def compute_kpis(self, equipment_dict: dict) -> list:
        if self.kpi_computer:
            try:
                return self.kpi_computer(equipment_dict)
            except Exception:
                pass
        return []
