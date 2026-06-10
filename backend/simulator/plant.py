"""
Plant simulator — motor de simulación data-driven.

Cada industria es un IndustryPlugin que define equipos, sensores, modos de falla
y condiciones iniciales. El motor no tiene lógica hardcodeada por industria.

Dirección de alerta por sensor:
  SensorDef.warning > SensorDef.critical  →  bajo es malo
  SensorDef.warning < SensorDef.critical  →  alto es malo
"""
import time
import random
from dataclasses import dataclass, field
from typing import Optional

from industries.base import IndustryPlugin, EquipmentDef


@dataclass
class Equipment:
    _config: EquipmentDef

    # Estado
    status: str = "running"          # running | warning | critical | maintenance | stopped
    health: float = 100.0
    degradation_rate: float = 0.0
    fault_mode: Optional[str] = None

    # Contadores
    operating_hours: float = 0.0
    last_maintenance: float = field(default_factory=time.time)

    # Sensores actuales
    sensors: dict = field(default_factory=dict)

    def __post_init__(self):
        lo, hi = self._config.initial_health_range
        self.health = random.uniform(lo, hi)
        dlo, dhi = self._config.base_degradation
        self.degradation_rate = random.uniform(dlo, dhi)
        # Inicializar sensores con valor nominal + pequeño jitter
        for key, sdef in self._config.sensors.items():
            self.sensors[key] = sdef.nominal + random.uniform(-sdef.nominal * 0.02,
                                                               sdef.nominal * 0.02)

    # ── Propiedades de conveniencia ───────────────────────────────────────────

    @property
    def id(self):   return self._config.eq_id
    @property
    def name(self): return self._config.name
    @property
    def area(self): return self._config.area

    # ── Tick principal ────────────────────────────────────────────────────────

    def tick(self, dt: float = 1.0):
        if self.status in ("maintenance", "stopped"):
            return

        self.operating_hours += dt / 3600.0
        self.health = max(0, self.health - self.degradation_rate * dt)

        # Probabilidad de falla espontánea (crece al degradarse)
        fault_prob = 0.0001 + (1 - self.health / 100) * 0.0005
        if self.fault_mode is None and random.random() < fault_prob * dt:
            self._inject_fault()

        self._update_sensors(dt)
        self._update_status()

    # ── Física de sensores ────────────────────────────────────────────────────

    def _update_sensors(self, dt: float):
        health_factor = self.health / 100.0

        for key, sdef in self._config.sensors.items():
            noise = random.gauss(0, sdef.nominal * sdef.noise_pct)

            # Deriva general por desgaste (sin falla)
            if sdef.is_low_sensor:
                # Sensor baja con degradación (caudal, presión, eficiencia, etc.)
                drift = -sdef.nominal * (1 - health_factor) * 0.22
            else:
                # Sensor sube con degradación (temperatura, vibración, H2S, etc.)
                drift = sdef.nominal * (1 - health_factor) * 0.28

            # Efecto adicional de la falla activa
            fault_effect = self._fault_effect(key, health_factor)

            raw = sdef.nominal + drift + fault_effect + noise
            self.sensors[key] = max(0.0, raw)

    def _fault_effect(self, sensor_key: str, health_factor: float) -> float:
        """
        Efecto del modo de falla activo sobre el sensor.
        Se escala por (1 - health_factor): más severo cuanto más degradado.
        """
        if not self.fault_mode:
            return 0.0
        fault = next((f for f in self._config.fault_modes
                      if f.mode_id == self.fault_mode), None)
        if not fault:
            return 0.0
        raw_effect = fault.sensor_effects.get(sensor_key, 0.0)
        return raw_effect * (1 - health_factor)

    # ── Estado según umbrales ─────────────────────────────────────────────────

    def _check_severity(self) -> str:
        for key, value in self.sensors.items():
            sdef = self._config.sensors.get(key)
            if not sdef:
                continue
            if sdef.is_low_sensor:
                if value < sdef.critical: return "critical"
                if value < sdef.warning:  return "warning"
            else:
                if value > sdef.critical: return "critical"
                if value > sdef.warning:  return "warning"
        return "ok"

    def _update_status(self):
        if self.status in ("maintenance", "stopped"):
            return
        sev = self._check_severity()
        if sev == "critical" or self.health < 20:
            self.status = "critical"
        elif sev == "warning" or self.health < 50:
            self.status = "warning"
        else:
            self.status = "running"

    # ── Acciones ──────────────────────────────────────────────────────────────

    def _inject_fault(self):
        if not self._config.fault_modes:
            return
        fault = random.choice(self._config.fault_modes)
        self.fault_mode = fault.mode_id
        self.degradation_rate *= fault.degradation_multiplier

    def inject_specific_fault(self, fault_mode_id: str) -> bool:
        """Inyecta un modo de falla específico. Retorna True si es válido."""
        fault = next((f for f in self._config.fault_modes
                      if f.mode_id == fault_mode_id), None)
        if not fault:
            return False
        self.fault_mode = fault_mode_id
        self.degradation_rate *= fault.degradation_multiplier
        return True

    def perform_maintenance(self):
        old = self.health
        self.health = min(100, self.health + random.uniform(30, 50))
        self.fault_mode = None
        dlo, dhi = self._config.base_degradation
        self.degradation_rate = random.uniform(dlo, dhi)
        self.status = "running"
        self.last_maintenance = time.time()
        return old, self.health

    def _fault_display_name(self) -> Optional[str]:
        if not self.fault_mode:
            return None
        fault = next((f for f in self._config.fault_modes
                      if f.mode_id == self.fault_mode), None)
        return fault.display_name if fault else self.fault_mode

    # ── Serialización ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id":               self._config.eq_id,
            "name":             self._config.name,
            "type":             self._config.eq_type,
            "icon":             self._config.icon,
            "area":             self._config.area,
            "criticality":      self._config.criticality,
            "status":           self.status,
            "health":           round(self.health, 1),
            "fault_mode":       self.fault_mode,
            "fault_mode_display": self._fault_display_name(),
            "operating_hours":  round(self.operating_hours, 1),
            "sensors":          {k: round(v, 3) for k, v in self.sensors.items()},
            "sensor_names":     {k: s.display_name for k, s in self._config.sensors.items()},
            "sensor_units":     {k: s.unit         for k, s in self._config.sensors.items()},
            "thresholds":       {
                k: {
                    "warning":  s.warning,
                    "critical": s.critical,
                    "unit":     s.unit,
                }
                for k, s in self._config.sensors.items()
            },
        }


class Plant:
    """Planta industrial — instancia una industria e impulsa la simulación."""

    def __init__(self, industry: IndustryPlugin = None):
        if industry is None:
            from industries import DEFAULT_INDUSTRY
            industry = DEFAULT_INDUSTRY

        self.industry = industry
        self.equipment: dict[str, Equipment] = {}
        self.tick_count = 0
        self.started_at = time.time()
        self._init_equipment()

    def _init_equipment(self):
        for eq_def in self.industry.equipment:
            self.equipment[eq_def.eq_id] = Equipment(_config=eq_def)

        # Aplicar condiciones iniciales definidas en el plugin
        for eq_id, cond in self.industry.initial_conditions.items():
            eq = self.equipment.get(eq_id)
            if not eq:
                continue
            if "health" in cond:
                eq.health = float(cond["health"])
            if "degradation_rate" in cond:
                eq.degradation_rate = float(cond["degradation_rate"])

    def tick(self, dt: float = 1.0):
        self.tick_count += 1
        for eq in self.equipment.values():
            eq.tick(dt)

    def get_snapshot(self) -> dict:
        eq_dict = {k: v.to_dict() for k, v in self.equipment.items()}
        n = max(len(self.equipment), 1)
        return {
            "tick":           self.tick_count,
            "timestamp":      time.time(),
            "uptime_seconds": round(time.time() - self.started_at),
            "industry": {
                "id":        self.industry.industry_id,
                "name":      self.industry.display_name,
                "icon":      self.industry.icon,
                "site_name": self.industry.site_name,
            },
            "equipment":  eq_dict,
            "plant_health": round(
                sum(e.health for e in self.equipment.values()) / n, 1
            ),
            "active_faults": [
                {
                    "equipment_id":   k,
                    "equipment_name": v.name,
                    "area":           v.area,
                    "fault":          v.fault_mode,
                    "fault_display":  v._fault_display_name(),
                }
                for k, v in self.equipment.items() if v.fault_mode
            ],
            "industry_kpis": self.industry.compute_kpis(eq_dict),
        }
