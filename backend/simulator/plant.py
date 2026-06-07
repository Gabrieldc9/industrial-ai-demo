"""
Plant simulator — manufactura genérica con 6 equipos.
Genera datos de sensores en tiempo real con degradación progresiva.
"""
import time
import math
import random
from dataclasses import dataclass, field
from typing import Optional

# ─── Tipos de equipo ────────────────────────────────────────────────────────

EQUIPMENT_CATALOG = {
    "PUMP-01":       {"name": "Bomba Centrífuga Principal",  "type": "pump",       "icon": "💧"},
    "COMP-01":       {"name": "Compresor de Aire",           "type": "compressor", "icon": "💨"},
    "CONV-01":       {"name": "Cinta Transportadora A",      "type": "conveyor",   "icon": "🔄"},
    "MOTOR-01":      {"name": "Motor Eléctrico #1",          "type": "motor",      "icon": "⚡"},
    "HEAT-01":       {"name": "Intercambiador de Calor",     "type": "heat_ex",    "icon": "🌡️"},
    "VALVE-01":      {"name": "Válvula de Control",          "type": "valve",      "icon": "🔧"},
}

# Umbrales de alerta y falla por tipo de sensor
SENSOR_THRESHOLDS = {
    "temperature": {"warning": 75.0,  "critical": 90.0,  "unit": "°C"},
    "vibration":   {"warning": 7.0,   "critical": 12.0,  "unit": "mm/s"},
    "pressure":    {"warning": 8.5,   "critical": 10.0,  "unit": "bar"},
    "current":     {"warning": 85.0,  "critical": 95.0,  "unit": "A"},
    "flow":        {"warning": 15.0,  "critical": 10.0,  "unit": "m³/h"},  # bajo = problema
    "efficiency":  {"warning": 75.0,  "critical": 60.0,  "unit": "%"},     # bajo = problema
}

# Sensores por tipo de equipo
EQUIPMENT_SENSORS = {
    "pump":       ["temperature", "vibration", "pressure", "flow", "current"],
    "compressor": ["temperature", "vibration", "pressure", "current", "efficiency"],
    "conveyor":   ["temperature", "vibration", "current", "efficiency"],
    "motor":      ["temperature", "vibration", "current"],
    "heat_ex":    ["temperature", "pressure", "flow", "efficiency"],
    "valve":      ["pressure", "flow"],
}

# Valores nominales por tipo de equipo (baseline saludable)
NOMINAL_VALUES = {
    "pump":       {"temperature": 45, "vibration": 2.5, "pressure": 6.0, "flow": 25.0, "current": 55},
    "compressor": {"temperature": 60, "vibration": 3.0, "pressure": 7.0, "current": 70, "efficiency": 90},
    "conveyor":   {"temperature": 40, "vibration": 2.0, "current": 45, "efficiency": 92},
    "motor":      {"temperature": 50, "vibration": 1.5, "current": 60},
    "heat_ex":    {"temperature": 55, "pressure": 5.5, "flow": 20.0, "efficiency": 88},
    "valve":      {"pressure": 4.0, "flow": 18.0},
}


@dataclass
class Equipment:
    id: str
    name: str
    eq_type: str
    icon: str

    # Estado
    status: str = "running"          # running | warning | critical | maintenance | stopped
    health: float = 100.0            # 0-100%
    degradation_rate: float = 0.0    # % por tick
    fault_mode: Optional[str] = None # None | bearing_wear | seal_leak | overload | misalignment | cavitation

    # Contadores
    operating_hours: float = 0.0
    uptime_since: float = field(default_factory=time.time)
    last_maintenance: float = field(default_factory=time.time)

    # Sensores actuales
    sensors: dict = field(default_factory=dict)

    def __post_init__(self):
        # Inicializar sensores con valores nominales + ruido
        nominal = NOMINAL_VALUES.get(self.eq_type, {})
        for sensor in EQUIPMENT_SENSORS.get(self.eq_type, []):
            base = nominal.get(sensor, 50.0)
            self.sensors[sensor] = base + random.uniform(-2, 2)
        # Degradación inicial aleatoria (los equipos no nacen nuevos)
        self.health = random.uniform(75, 100)
        self.degradation_rate = random.uniform(0.002, 0.008)  # % por tick (lento)

    def tick(self, dt: float = 1.0):
        """Avanza la simulación un tick (dt segundos)."""
        if self.status in ("maintenance", "stopped"):
            return

        self.operating_hours += dt / 3600.0

        # Degradación base
        self.health = max(0, self.health - self.degradation_rate * dt)

        # Inyección de falla espontánea (probabilidad baja, mayor cuando health < 50)
        fault_prob = 0.0001 + (1 - self.health / 100) * 0.0005
        if self.fault_mode is None and random.random() < fault_prob * dt:
            self._inject_fault()

        # Actualizar sensores según health + fault_mode
        self._update_sensors(dt)

        # Actualizar status según sensores
        self._update_status()

    def _inject_fault(self):
        fault_options = {
            "pump":       ["bearing_wear", "seal_leak", "cavitation"],
            "compressor": ["bearing_wear", "overload", "valve_wear"],
            "conveyor":   ["bearing_wear", "misalignment", "belt_slip"],
            "motor":      ["overload", "bearing_wear", "insulation_degradation"],
            "heat_ex":    ["fouling", "seal_leak"],
            "valve":      ["seal_leak", "actuator_fault"],
        }
        options = fault_options.get(self.eq_type, ["generic_fault"])
        self.fault_mode = random.choice(options)
        # Acelerar degradación
        self.degradation_rate *= random.uniform(3, 8)

    def _update_sensors(self, dt: float):
        nominal = NOMINAL_VALUES.get(self.eq_type, {})
        health_factor = self.health / 100.0  # 1.0 = perfecto, 0.0 = muerto

        for sensor, base_val in nominal.items():
            noise = random.gauss(0, base_val * 0.01)  # 1% ruido
            degradation_effect = 0.0

            if self.fault_mode:
                degradation_effect = self._fault_effect(sensor, health_factor)

            # Temperatura y vibración suben con degradación
            if sensor in ("temperature", "vibration", "current"):
                drift = base_val * (1 - health_factor) * 0.5
                self.sensors[sensor] = base_val + drift + degradation_effect + noise
            # Flow y efficiency bajan con degradación
            elif sensor in ("flow", "efficiency"):
                drift = base_val * (1 - health_factor) * 0.3
                self.sensors[sensor] = max(0, base_val - drift - abs(degradation_effect) + noise)
            # Presión puede subir o bajar
            elif sensor == "pressure":
                if self.fault_mode in ("seal_leak",):
                    self.sensors[sensor] = max(0, base_val - abs(degradation_effect) + noise)
                else:
                    self.sensors[sensor] = base_val + degradation_effect * 0.5 + noise
            else:
                self.sensors[sensor] = base_val + noise

    def _fault_effect(self, sensor: str, health_factor: float) -> float:
        """Amplitud del efecto de la falla actual en el sensor."""
        magnitude = (1 - health_factor) * 15  # más severo cuando más degradado
        fault_sensor_map = {
            "bearing_wear":             {"vibration": magnitude * 1.5, "temperature": magnitude},
            "seal_leak":                {"pressure": -magnitude, "flow": -magnitude * 0.5},
            "cavitation":               {"vibration": magnitude, "flow": -magnitude},
            "overload":                 {"current": magnitude * 1.2, "temperature": magnitude},
            "misalignment":             {"vibration": magnitude * 2, "temperature": magnitude * 0.5},
            "fouling":                  {"temperature": magnitude, "efficiency": -magnitude},
            "valve_wear":               {"pressure": magnitude * 0.5},
            "belt_slip":                {"efficiency": -magnitude, "vibration": magnitude * 0.5},
            "insulation_degradation":   {"current": magnitude, "temperature": magnitude * 0.5},
            "actuator_fault":           {"flow": -magnitude},
        }
        effects = fault_sensor_map.get(self.fault_mode or "", {})
        return effects.get(sensor, 0.0)

    def _update_status(self):
        prev = self.status
        if self.status in ("maintenance", "stopped"):
            return

        severity = self._check_severity()
        if severity == "critical" or self.health < 20:
            self.status = "critical"
        elif severity == "warning" or self.health < 50:
            self.status = "warning"
        else:
            self.status = "running"

    def _check_severity(self) -> str:
        for sensor, value in self.sensors.items():
            thresh = SENSOR_THRESHOLDS.get(sensor)
            if not thresh:
                continue
            crit = thresh["critical"]
            warn = thresh["warning"]
            # Para sensores "bajo = problema"
            if sensor in ("flow", "efficiency"):
                if value < crit:
                    return "critical"
                if value < warn:
                    return "warning"
            else:
                if value > crit:
                    return "critical"
                if value > warn:
                    return "warning"
        return "ok"

    def perform_maintenance(self):
        """Resetea el equipo tras intervención de mantenimiento."""
        old_health = self.health
        self.health = min(100, self.health + random.uniform(30, 50))
        self.fault_mode = None
        self.degradation_rate = random.uniform(0.002, 0.008)
        self.status = "running"
        self.last_maintenance = time.time()
        return old_health, self.health

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.eq_type,
            "icon": self.icon,
            "status": self.status,
            "health": round(self.health, 1),
            "fault_mode": self.fault_mode,
            "operating_hours": round(self.operating_hours, 1),
            "sensors": {k: round(v, 2) for k, v in self.sensors.items()},
            "sensor_units": {s: SENSOR_THRESHOLDS[s]["unit"] for s in self.sensors if s in SENSOR_THRESHOLDS},
            "thresholds": {s: SENSOR_THRESHOLDS[s] for s in self.sensors if s in SENSOR_THRESHOLDS},
        }


class Plant:
    """Planta de manufactura genérica."""

    def __init__(self):
        self.equipment: dict[str, Equipment] = {}
        self.tick_count = 0
        self.started_at = time.time()
        self._init_equipment()

    def _init_equipment(self):
        for eq_id, meta in EQUIPMENT_CATALOG.items():
            self.equipment[eq_id] = Equipment(
                id=eq_id,
                name=meta["name"],
                eq_type=meta["type"],
                icon=meta["icon"],
            )
        # Arrancar con algunos equipos ya degradados para que la demo sea interesante
        self.equipment["PUMP-01"].health = 55.0
        self.equipment["PUMP-01"].degradation_rate = 0.015
        self.equipment["MOTOR-01"].health = 68.0

    def tick(self, dt: float = 1.0):
        self.tick_count += 1
        for eq in self.equipment.values():
            eq.tick(dt)

    def get_snapshot(self) -> dict:
        return {
            "tick": self.tick_count,
            "timestamp": time.time(),
            "uptime_seconds": round(time.time() - self.started_at),
            "equipment": {k: v.to_dict() for k, v in self.equipment.items()},
            "plant_health": round(
                sum(e.health for e in self.equipment.values()) / len(self.equipment), 1
            ),
            "active_faults": [
                {"equipment_id": k, "fault": v.fault_mode}
                for k, v in self.equipment.items()
                if v.fault_mode
            ],
        }
