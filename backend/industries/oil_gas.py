"""
Oil & Gas — Batería de Producción convencional.

Inspirado en operaciones típicas de Vaca Muerta / cuencas argentinas.
9 equipos en 5 áreas: Pozos · Separación · Compresión · Almacenamiento · Utilities
"""
from .base import IndustryPlugin, EquipmentDef, SensorDef, FaultMode

# ─── Helpers KPI ──────────────────────────────────────────────────────────────

def _kpi_status(value, warn_threshold, crit_threshold, low_is_bad=False):
    if low_is_bad:
        return "critical" if value < crit_threshold else "warning" if value < warn_threshold else "ok"
    return "critical" if value > crit_threshold else "warning" if value > warn_threshold else "ok"


def _compute_oil_gas_kpis(eq_dict: dict) -> list:
    """Calcula KPIs específicos de la batería O&G en tiempo real."""
    wells   = {k: v for k, v in eq_dict.items() if k.startswith("WELL-")}
    active  = [v for v in wells.values() if v["status"] not in ("stopped",)]

    # Producción en bbl/día (conversión m³/d × 6.2898)
    total_m3d   = sum(w["sensors"].get("flow_rate", 0) for w in active)
    total_bbl   = round(total_m3d * 6.2898)
    prod_status = _kpi_status(total_bbl, 900, 600, low_is_bad=True)

    # Water Cut promedio (%)
    avg_wc = (
        round(sum(w["sensors"].get("water_cut", 0) for w in active) / len(active), 1)
        if active else 0
    )
    wc_status = _kpi_status(avg_wc, 35, 50)

    # H2S máximo (ppm) — indicador de seguridad crítico
    tank = eq_dict.get("TANK-01", {})
    h2s  = round(tank.get("sensors", {}).get("h2s_ppm", 0), 1)
    h2s_status = _kpi_status(h2s, 10, 50)

    # Compresor de gas
    comp   = eq_dict.get("COMP-01", {})
    c_stat = comp.get("status", "stopped")
    comp_ok = c_stat not in ("stopped",)
    comp_label = "Online" if c_stat == "running" else ("⚠ Alerta" if comp_ok else "Offline")

    # Pozos activos
    n_active = len(active)
    n_total  = len(wells)
    wells_status = "ok" if n_active == n_total else "warning" if n_active >= n_total // 2 else "critical"

    return [
        {"label": "Producción",    "value": f"{total_bbl:,}",       "unit": "bbl/día",  "status": prod_status},
        {"label": "Water Cut",     "value": str(avg_wc),             "unit": "%",        "status": wc_status},
        {"label": "H2S máx",       "value": str(h2s),                "unit": "ppm",      "status": h2s_status},
        {"label": "Compresor",     "value": comp_label,              "unit": "",         "status": "ok" if comp_ok else "critical"},
        {"label": "Pozos activos", "value": f"{n_active}/{n_total}", "unit": "",         "status": wells_status},
    ]


# ─── Definición de equipos ────────────────────────────────────────────────────

# Sensores compartidos entre pozos (con nombres en español)
def _well_sensors(nominal_pressure, nominal_flow, nominal_wc):
    return {
        "wh_pressure":  SensorDef("Presión cabeza",  "bar",    nominal_pressure, 90,  65),  # low=bad
        "temperature":  SensorDef("Temperatura",      "°C",     68,               82,  95),  # high=bad
        "flow_rate":    SensorDef("Caudal",           "m³/d",   nominal_flow,     110, 70),  # low=bad
        "water_cut":    SensorDef("Water cut",        "%",      nominal_wc,       38,  52),  # high=bad
        "gor":          SensorDef("GOR",              "m³/m³",  148,              205, 290), # high=bad
    }

# Modos de falla comunes a los tres pozos
_WELL_FAULTS = [
    FaultMode("sand_influx",        "Influx de arena",
              {"wh_pressure": -30, "flow_rate": -80,  "water_cut": +8,  "gor": +30},
              degradation_multiplier=4.0),
    FaultMode("hydrate_formation",  "Formación de hidratos",
              {"wh_pressure": -50, "flow_rate": -150, "temperature": -5},
              degradation_multiplier=7.0),
    FaultMode("scale_buildup",      "Incrustaciones",
              {"flow_rate": -60,   "wh_pressure": -25},
              degradation_multiplier=3.0),
    FaultMode("wax_deposition",     "Depósito de cera",
              {"flow_rate": -70,   "wh_pressure": -30, "temperature": +3},
              degradation_multiplier=3.5),
]

OIL_GAS_BATERIA = IndustryPlugin(
    industry_id="oil_gas_bateria",
    display_name="Oil & Gas — Batería de Producción",
    icon="🛢️",
    description="Batería de producción convencional: 3 pozos, separación, compresión y almacenamiento.",
    site_name="Batería Norte — Cuenca Neuquina",
    kpi_computer=_compute_oil_gas_kpis,

    equipment=[

        # ── ÁREA: POZOS ──────────────────────────────────────────────────────────

        EquipmentDef(
            eq_id="WELL-01", name="Pozo NOC-01", eq_type="wellhead", icon="🔩",
            area="Pozos",
            sensors=_well_sensors(nominal_pressure=118, nominal_flow=185, nominal_wc=16),
            fault_modes=_WELL_FAULTS,
            initial_health_range=(82, 96),
            criticality="high",
        ),

        EquipmentDef(
            eq_id="WELL-02", name="Pozo NOC-02", eq_type="wellhead", icon="🔩",
            area="Pozos",
            sensors=_well_sensors(nominal_pressure=112, nominal_flow=162, nominal_wc=21),
            fault_modes=_WELL_FAULTS,
            initial_health_range=(78, 92),
            criticality="high",
        ),

        EquipmentDef(
            eq_id="WELL-03", name="Pozo NOC-03", eq_type="wellhead", icon="🔩",
            area="Pozos",
            # Pozo más viejo: mayor water cut, menor presión
            sensors={
                "wh_pressure":  SensorDef("Presión cabeza",  "bar",    95,  90, 65),
                "temperature":  SensorDef("Temperatura",      "°C",     72,  82, 95),
                "flow_rate":    SensorDef("Caudal",           "m³/d",   128, 110, 70),
                "water_cut":    SensorDef("Water cut",        "%",      34,  38, 52),
                "gor":          SensorDef("GOR",              "m³/m³",  175, 205, 290),
            },
            fault_modes=_WELL_FAULTS,
            initial_health_range=(55, 72),   # arranca degradado para que la demo sea interesante
            criticality="high",
        ),

        # ── ÁREA: SEPARACIÓN ─────────────────────────────────────────────────────

        EquipmentDef(
            eq_id="SEP-01", name="Separador Trifásico", eq_type="separator_3ph", icon="⚗️",
            area="Separación",
            sensors={
                "inlet_pressure": SensorDef("Presión entrada",   "bar",   12.0, 16.0, 19.0),  # high=bad
                "temperature":    SensorDef("Temperatura",        "°C",    48.0, 62.0, 78.0),  # high=bad
                "oil_level":      SensorDef("Nivel aceite",       "%",     52.0, 20.0, 10.0),  # low=bad
                "bsw":            SensorDef("BSW",                "%",     0.30, 0.85, 1.60),  # high=bad (calidad)
                "gas_flow":       SensorDef("Flujo gas",          "Mm³/d", 0.25, 0.12, 0.07),  # low=bad
            },
            fault_modes=[
                FaultMode("emulsion_stable",       "Emulsión estable",
                          {"bsw": +1.5,  "oil_level": +20},    4.0),
                FaultMode("level_valve_failure",   "Falla válvula de nivel",
                          {"oil_level": +35, "bsw": +0.8},     5.0),
                FaultMode("foam_problem",          "Problema de espuma",
                          {"gas_flow": -0.1, "bsw": +0.5, "oil_level": +15}, 3.5),
                FaultMode("corrosion_internal",    "Corrosión interna",
                          {"inlet_pressure": -2, "bsw": +0.4}, 3.0),
            ],
            initial_health_range=(80, 95),
            criticality="critical",
        ),

        EquipmentDef(
            eq_id="TREAT-01", name="Heater Treater", eq_type="heater_treater", icon="🔥",
            area="Separación",
            sensors={
                "temperature":        SensorDef("Temperatura",        "°C",  72.0, 58.0, 48.0),  # low=bad (quemador)
                "inlet_pressure":     SensorDef("Presión entrada",    "bar",  8.0, 12.0, 15.0),   # high=bad
                "bsw_out":            SensorDef("BSW salida",         "%",   0.22, 0.80, 1.50),   # high=bad
                "burner_efficiency":  SensorDef("Efic. quemador",     "%",   88.0, 68.0, 52.0),   # low=bad
            },
            fault_modes=[
                FaultMode("burner_failure",      "Falla quemador",
                          {"temperature": -25, "bsw_out": +1.5, "burner_efficiency": -40}, 6.0),
                FaultMode("heat_loss_fouling",   "Fouling intercambiador",
                          {"temperature": -10, "bsw_out": +0.8, "burner_efficiency": -20}, 3.0),
                FaultMode("emulsion_overstable", "Emulsión sobrestable",
                          {"bsw_out": +1.0,  "temperature": +5}, 3.5),
                FaultMode("fuel_shortage",       "Falta de combustible",
                          {"burner_efficiency": -30, "temperature": -15, "bsw_out": +0.8}, 5.0),
            ],
            initial_health_range=(78, 93),
            criticality="high",
        ),

        # ── ÁREA: COMPRESIÓN ─────────────────────────────────────────────────────

        EquipmentDef(
            eq_id="COMP-01", name="Compresor Gas — Reciprocante", eq_type="gas_compressor", icon="💨",
            area="Compresión",
            sensors={
                "suction_pressure":    SensorDef("Presión succión",   "bar",   8.0, 5.0,  3.0),   # low=bad
                "discharge_pressure":  SensorDef("Presión descarga",  "bar",  32.0, 26.0, 22.0),  # low=bad
                "temperature":         SensorDef("Temperatura",        "°C",   88.0, 105.0, 120.0), # high=bad
                "vibration":           SensorDef("Vibración",          "mm/s",  4.2,   7.0,  11.0),  # high=bad
                "valve_health":        SensorDef("Salud válvulas",     "%",    92.0,  68.0,  50.0),  # low=bad
            },
            fault_modes=[
                FaultMode("valve_failure",    "Falla válvulas",
                          {"discharge_pressure": -12, "temperature": +18, "valve_health": -45}, 5.0),
                FaultMode("rod_seal_leak",    "Fuga sello de vástago",
                          {"discharge_pressure": -8,  "temperature": +10, "vibration": +2.0},   4.5),
                FaultMode("lube_oil_failure", "Falla sistema lubricación",
                          {"temperature": +22, "vibration": +3.5, "discharge_pressure": -5},   6.0),
                FaultMode("cooler_fouling",   "Fouling en enfriador",
                          {"temperature": +30, "discharge_pressure": -4}, 3.5),
            ],
            initial_health_range=(70, 88),  # compresor ya con algo de uso
            criticality="critical",
        ),

        # ── ÁREA: ALMACENAMIENTO ─────────────────────────────────────────────────

        EquipmentDef(
            eq_id="PUMP-01", name="Bomba Transferencia Crudo", eq_type="transfer_pump", icon="💧",
            area="Almacenamiento",
            sensors={
                "flow_rate":          SensorDef("Caudal",          "m³/h",  48.0, 30.0, 18.0),   # low=bad
                "discharge_pressure": SensorDef("Presión descarga", "bar",   14.0, 10.0,  7.0),   # low=bad
                "temperature":        SensorDef("Temperatura",      "°C",    58.0, 72.0, 88.0),   # high=bad
                "vibration":          SensorDef("Vibración",        "mm/s",   3.1,  6.5, 10.5),   # high=bad
                "current":            SensorDef("Corriente",        "A",     68.0, 82.0, 95.0),   # high=bad
            },
            fault_modes=[
                FaultMode("impeller_wear",       "Desgaste impulsor",
                          {"flow_rate": -20, "discharge_pressure": -5, "vibration": +1.5}, 4.0),
                FaultMode("mechanical_seal_failure", "Falla sello mecánico",
                          {"discharge_pressure": -4, "flow_rate": -10, "temperature": +8}, 4.5),
                FaultMode("cavitation",          "Cavitación",
                          {"vibration": +5, "flow_rate": -18, "current": +10}, 5.0),
                FaultMode("bearing_overheating", "Sobrecalentamiento rodamientos",
                          {"temperature": +18, "vibration": +4}, 4.0),
            ],
            initial_health_range=(80, 95),
            criticality="high",
        ),

        EquipmentDef(
            eq_id="TANK-01", name="Tanque Almacenamiento Crudo", eq_type="storage_tank", icon="🛢️",
            area="Almacenamiento",
            sensors={
                "level":          SensorDef("Nivel",           "%",    55.0, 20.0, 10.0),    # low=bad (también 90% high=bad)
                "temperature":    SensorDef("Temperatura",     "°C",   38.0, 52.0, 62.0),    # high=bad
                "h2s_ppm":        SensorDef("H2S",             "ppm",   3.0, 10.0, 50.0),    # high=bad (seguridad crítica)
                "vapor_pressure": SensorDef("Presión vapor",   "mbar", 45.0, 82.0, 105.0),   # high=bad
            },
            fault_modes=[
                FaultMode("h2s_accumulation",          "Acumulación H2S",    # ← evento de seguridad
                          {"h2s_ppm": +60, "vapor_pressure": +25}, 5.0),
                FaultMode("level_transmitter_failure", "Falla transmisor nivel",
                          {"level": -30}, 2.0),
                FaultMode("floating_roof_stuck",       "Techo flotante trabado",
                          {"vapor_pressure": +45, "h2s_ppm": +20}, 4.0),
                FaultMode("bottom_corrosion",          "Corrosión fondo",
                          {"h2s_ppm": +10, "level": -8}, 2.5),
            ],
            initial_health_range=(82, 96),
            criticality="medium",
        ),

        # ── ÁREA: UTILITIES ──────────────────────────────────────────────────────

        EquipmentDef(
            eq_id="GEN-01", name="Generador a Gas", eq_type="gas_generator", icon="⚡",
            area="Utilities",
            sensors={
                "voltage":    SensorDef("Voltaje",     "V",    480.0, 460.0, 440.0),  # low=bad
                "frequency":  SensorDef("Frecuencia",  "Hz",    60.0,  58.5,  57.0),  # low=bad
                "temperature": SensorDef("Temperatura", "°C",   78.0,  95.0, 110.0),  # high=bad
                "load_pct":   SensorDef("Carga",       "%",     68.0,  85.0,  95.0),  # high=bad
                "fuel_flow":  SensorDef("Flujo comb.", "m³/h",  16.0,   9.0,   5.0),  # low=bad
            },
            fault_modes=[
                FaultMode("cooling_failure",  "Falla sistema refrigeración",
                          {"temperature": +28, "load_pct": +15}, 5.0),
                FaultMode("governor_failure", "Falla gobernador",
                          {"frequency": -3,   "voltage": -15}, 5.5),
                FaultMode("alternator_fault", "Falla alternador",
                          {"voltage": -25,    "temperature": +15}, 4.5),
                FaultMode("fuel_shortage",    "Falta combustible",
                          {"fuel_flow": -8,   "frequency": -2,  "load_pct": -20}, 5.0),
            ],
            initial_health_range=(82, 96),
            criticality="critical",
        ),

        EquipmentDef(
            eq_id="FLARE-01", name="Sistema de Antorcha", eq_type="flare_system", icon="🔆",
            area="Utilities",
            sensors={
                "flare_rate":  SensorDef("Caudal venteo",  "Mm³/d", 0.04, 0.15, 0.30),  # high=bad (ambiental)
                "pilot_temp":  SensorDef("Temp. piloto",   "°C",   850.0, 400.0, 300.0), # low=bad (seguridad)
                "h2s_flare":   SensorDef("H2S en venteo",  "ppm",    0.1,   5.0,  15.0), # high=bad
            },
            fault_modes=[
                FaultMode("pilot_extinguished",     "Piloto apagado",         # ← evento ambiental/seguridad
                          {"pilot_temp": -600, "flare_rate": +0.25, "h2s_flare": +10}, 8.0),
                FaultMode("excessive_flaring",      "Venteo excesivo",
                          {"flare_rate": +0.30, "h2s_flare": +8}, 4.0),
                FaultMode("liquid_carryover",       "Arrastre de líquido",
                          {"pilot_temp": -200, "flare_rate": +0.10}, 3.5),
                FaultMode("pilot_ignition_failure", "Falla ignición piloto",
                          {"pilot_temp": -300, "flare_rate": +0.15}, 6.0),
            ],
            initial_health_range=(85, 98),
            criticality="high",
        ),
    ],

    # Condiciones iniciales para demo interesante desde el minuto 0
    initial_conditions={
        "WELL-03": {"health": 62.0, "degradation_rate": 0.012},  # pozo viejo ya degradado
        "COMP-01": {"health": 75.0, "degradation_rate": 0.008},  # compresor con uso
    },
)
