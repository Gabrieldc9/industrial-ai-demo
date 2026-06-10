"""
Manufactura genérica — los 6 equipos originales, ahora como IndustryPlugin.
Mantiene backward compatibility con la demo anterior.
"""
from .base import IndustryPlugin, EquipmentDef, SensorDef, FaultMode


def _compute_generic_kpis(eq_dict: dict) -> list:
    equip   = list(eq_dict.values())
    running = [e for e in equip if e["status"] == "running"]
    health  = round(sum(e["health"] for e in equip) / max(len(equip), 1), 1)

    oee = round(len(running) / max(len(equip), 1) * 100, 1)
    h_status = "ok" if health > 70 else "warning" if health > 40 else "critical"

    return [
        {"label": "OEE Planta",   "value": str(oee),        "unit": "%",     "status": h_status},
        {"label": "Eq. operando", "value": f"{len(running)}/{len(equip)}", "unit": "", "status": "ok" if len(running) == len(equip) else "warning"},
    ]


# Sensores estándar reutilizables
def _s(display, unit, nominal, warning, critical):
    return SensorDef(display, unit, nominal, warning, critical)


GENERIC_MANUFACTURING = IndustryPlugin(
    industry_id="generic_manufacturing",
    display_name="Manufactura Genérica",
    icon="🏭",
    description="Planta de manufactura genérica con 6 equipos de proceso.",
    site_name="Planta Piloto",
    kpi_computer=_compute_generic_kpis,

    equipment=[
        EquipmentDef(
            eq_id="PUMP-01", name="Bomba Centrífuga Principal", eq_type="pump", icon="💧",
            area="Proceso",
            sensors={
                "temperature": _s("Temperatura", "°C",    45.0, 75.0, 90.0),
                "vibration":   _s("Vibración",   "mm/s",   2.5,  7.0, 12.0),
                "pressure":    _s("Presión",     "bar",    6.0,  8.5, 10.0),
                "flow":        _s("Caudal",      "m³/h",  25.0, 15.0, 10.0),
                "current":     _s("Corriente",   "A",     55.0, 85.0, 95.0),
            },
            fault_modes=[
                FaultMode("bearing_wear",  "Desgaste rodamiento", {"vibration": +12, "temperature": +20}, 5.0),
                FaultMode("seal_leak",     "Fuga sello",          {"pressure": -3,   "flow": -8},         4.0),
                FaultMode("cavitation",    "Cavitación",          {"vibration": +10, "flow": -10},        5.0),
            ],
            initial_health_range=(50, 70),
        ),
        EquipmentDef(
            eq_id="COMP-01", name="Compresor de Aire", eq_type="compressor", icon="💨",
            area="Utilities",
            sensors={
                "temperature": _s("Temperatura", "°C",    60.0,  75.0, 90.0),
                "vibration":   _s("Vibración",   "mm/s",   3.0,   7.0, 12.0),
                "pressure":    _s("Presión",     "bar",    7.0,   8.5, 10.0),
                "current":     _s("Corriente",   "A",     70.0,  85.0, 95.0),
                "efficiency":  _s("Eficiencia",  "%",     90.0,  75.0, 60.0),
            },
            fault_modes=[
                FaultMode("bearing_wear", "Desgaste rodamiento", {"vibration": +12, "temperature": +15}, 5.0),
                FaultMode("overload",     "Sobrecarga",          {"current": +18,   "temperature": +20}, 5.0),
                FaultMode("valve_wear",   "Desgaste válvulas",   {"pressure": +3,   "efficiency": -25},  4.0),
            ],
            initial_health_range=(70, 90),
        ),
        EquipmentDef(
            eq_id="CONV-01", name="Cinta Transportadora A", eq_type="conveyor", icon="🔄",
            area="Proceso",
            sensors={
                "temperature": _s("Temperatura", "°C",   40.0, 75.0, 90.0),
                "vibration":   _s("Vibración",   "mm/s",  2.0,  7.0, 12.0),
                "current":     _s("Corriente",   "A",    45.0, 85.0, 95.0),
                "efficiency":  _s("Eficiencia",  "%",    92.0, 75.0, 60.0),
            },
            fault_modes=[
                FaultMode("bearing_wear",  "Desgaste rodamiento", {"vibration": +12, "temperature": +15}, 5.0),
                FaultMode("misalignment",  "Desalineación",       {"vibration": +20, "temperature": +8},  4.0),
                FaultMode("belt_slip",     "Deslizamiento correa",{"efficiency": -30, "vibration": +5},   3.5),
            ],
            initial_health_range=(75, 95),
        ),
        EquipmentDef(
            eq_id="MOTOR-01", name="Motor Eléctrico #1", eq_type="motor", icon="⚡",
            area="Proceso",
            sensors={
                "temperature": _s("Temperatura", "°C",   50.0, 75.0, 90.0),
                "vibration":   _s("Vibración",   "mm/s",  1.5,  7.0, 12.0),
                "current":     _s("Corriente",   "A",    60.0, 85.0, 95.0),
            },
            fault_modes=[
                FaultMode("overload",               "Sobrecarga",            {"current": +22, "temperature": +18}, 5.0),
                FaultMode("bearing_wear",           "Desgaste rodamiento",   {"vibration": +12, "temperature": +12}, 5.0),
                FaultMode("insulation_degradation", "Degrad. aislamiento",   {"current": +15, "temperature": +10}, 4.0),
            ],
            initial_health_range=(65, 85),
        ),
        EquipmentDef(
            eq_id="HEAT-01", name="Intercambiador de Calor", eq_type="heat_ex", icon="🌡️",
            area="Proceso",
            sensors={
                "temperature": _s("Temperatura", "°C",   55.0, 75.0, 90.0),
                "pressure":    _s("Presión",     "bar",   5.5,  8.5, 10.0),
                "flow":        _s("Caudal",      "m³/h", 20.0, 15.0, 10.0),
                "efficiency":  _s("Eficiencia",  "%",    88.0, 75.0, 60.0),
            },
            fault_modes=[
                FaultMode("fouling",   "Ensuciamiento",  {"temperature": +18, "efficiency": -28}, 3.5),
                FaultMode("seal_leak", "Fuga sello",     {"pressure": -2,     "flow": -6},        4.0),
            ],
            initial_health_range=(75, 95),
        ),
        EquipmentDef(
            eq_id="VALVE-01", name="Válvula de Control", eq_type="valve", icon="🔧",
            area="Proceso",
            sensors={
                "pressure": _s("Presión", "bar",   4.0,  8.5, 10.0),
                "flow":     _s("Caudal",  "m³/h", 18.0, 15.0, 10.0),
            },
            fault_modes=[
                FaultMode("seal_leak",     "Fuga sello",    {"pressure": -3, "flow": -5}, 4.0),
                FaultMode("actuator_fault","Falla actuador",{"flow": -12},                4.0),
            ],
            initial_health_range=(80, 98),
        ),
    ],

    initial_conditions={
        "PUMP-01":  {"health": 55.0, "degradation_rate": 0.015},
        "MOTOR-01": {"health": 68.0},
    },
)
