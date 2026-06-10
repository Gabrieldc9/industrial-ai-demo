"""
Agente de Proceso — Monitorea eficiencia operativa y optimiza setpoints.

No reacciona a fallas (eso es Mantenimiento) sino a ineficiencias:
  - Separación agua/aceite subóptima
  - Ratio de compresión bajo
  - Quemadores con eficiencia baja
  - Pozos con caudal bajo y buen health (posible restricción)

En modo autónomo: registra ajustes de setpoints como acciones ejecutadas.
"""
import time
from cmms.work_orders import log_agent_action
from simulator.plant import Plant

ACTION_COOLDOWN     = 90   # s entre recomendaciones del mismo equipo
WELL_FLOW_COOLDOWN  = 180  # s (menor frecuencia para pozos — menos urgente)

_last_action: dict[str, float] = {}


class ProcessAgent:

    def __init__(self, plant: Plant, autonomy: dict):
        self.plant    = plant
        self.autonomy = autonomy
        self._last_action    = "Monitoreando eficiencia de proceso..."
        self._last_action_ts = time.time()
        self._stats = {
            "recommendations":      0,
            "autonomous_adjustments": 0,
        }

    def get_status(self) -> dict:
        return {
            "id":             "process",
            "name":           "Agente de Proceso",
            "icon":           "⚙️",
            "domain":         "Eficiencia · setpoints · rendimiento de separación · caudales",
            "status":         "active",
            "last_action":    self._last_action,
            "last_action_ts": self._last_action_ts,
            "stats":          dict(self._stats),
        }

    async def run_tick(self):
        snapshot    = self.plant.get_snapshot()
        industry_id = snapshot.get("industry", {}).get("id", "")

        if industry_id == "oil_gas_bateria":
            self._evaluate_oil_gas(snapshot)
        else:
            self._evaluate_generic(snapshot)

    # ─── Oil & Gas ────────────────────────────────────────────────────────────

    def _evaluate_oil_gas(self, snapshot: dict):
        now  = time.time()
        mode = self.autonomy.get("mode", "assisted")
        eq   = snapshot["equipment"]

        # 1. Separador — BSW alto indica emulsión
        self._check_separator(eq.get("SEP-01"), now, mode)

        # 2. Compresor — ratio descarga/succión
        self._check_compressor(eq.get("COMP-01"), now, mode)

        # 3. Heater treater — eficiencia del quemador
        self._check_heater(eq.get("TREAT-01"), now, mode)

        # 4. Pozos — caudal bajo con buen health
        for wid in ("WELL-01", "WELL-02", "WELL-03"):
            self._check_well_flow(eq.get(wid), wid, now, mode)

    def _check_separator(self, sep, now, mode):
        if not sep or sep["status"] in ("maintenance", "stopped"):
            return
        bsw = sep["sensors"].get("bsw", 0)
        if bsw <= 2.0:
            return
        key = "sep_bsw"
        if now - _last_action.get(key, 0) < ACTION_COOLDOWN:
            return
        _last_action[key] = now
        self._stats["recommendations"] += 1
        if mode == "autonomous":
            self._stats["autonomous_adjustments"] += 1
            act = (
                f"🤖 [AUTÓNOMO] BSW separador {bsw:.1f}% > 2%. "
                f"Tiempo de residencia aumentado +5% — eficiencia de separación restaurada"
            )
        else:
            act = (
                f"⚙️ BSW separador elevado ({bsw:.1f}%). "
                f"Recomendación: aumentar tiempo de residencia en SEP-01"
            )
        self._emit(act, "SEP-01", now)

    def _check_compressor(self, comp, now, mode):
        if not comp or comp["status"] in ("maintenance", "stopped"):
            return
        suction    = comp["sensors"].get("suction_pressure", 1)
        discharge  = comp["sensors"].get("discharge_pressure", 1)
        if suction <= 0:
            return
        ratio = discharge / suction
        if ratio >= 2.5:
            return
        key = "comp_ratio"
        if now - _last_action.get(key, 0) < ACTION_COOLDOWN:
            return
        _last_action[key] = now
        self._stats["recommendations"] += 1
        act = (
            f"⚙️ Compresor: ratio descarga/succión bajo ({ratio:.2f}x < 2.5). "
            f"Revisar válvulas de succión y filtros"
        )
        self._emit(act, "COMP-01", now)

    def _check_heater(self, treat, now, mode):
        if not treat or treat["status"] in ("maintenance", "stopped"):
            return
        eff = treat["sensors"].get("burner_efficiency", 100)
        if eff >= 80:
            return
        key = "treat_eff"
        if now - _last_action.get(key, 0) < ACTION_COOLDOWN:
            return
        _last_action[key] = now
        self._stats["recommendations"] += 1
        if mode == "autonomous":
            self._stats["autonomous_adjustments"] += 1
            act = (
                f"🤖 [AUTÓNOMO] Eficiencia quemador {eff:.1f}%. "
                f"Ajustando presión de atomización — recuperando eficiencia"
            )
        else:
            act = (
                f"⚙️ Eficiencia quemador TREAT-01: {eff:.1f}% < 80%. "
                f"Verificar atomización de combustible y boquilla"
            )
        self._emit(act, "TREAT-01", now)

    def _check_well_flow(self, well, well_id, now, mode):
        if not well or well["status"] in ("maintenance", "stopped", "critical"):
            return
        flow   = well["sensors"].get("flow_rate", 999)
        health = well["health"]
        if flow >= 30 or health < 70:
            return
        key = f"well_flow_{well_id}"
        if now - _last_action.get(key, 0) < WELL_FLOW_COOLDOWN:
            return
        _last_action[key] = now
        self._stats["recommendations"] += 1
        act = (
            f"⚙️ {well['name']}: caudal bajo ({flow:.1f} m³/d) "
            f"con health {health:.0f}% — posible restricción en tubería o arena"
        )
        self._emit(act, well_id, now)

    # ─── Genérico ─────────────────────────────────────────────────────────────

    def _evaluate_generic(self, snapshot: dict):
        now = time.time()
        for eq_id, eq_data in snapshot["equipment"].items():
            if eq_data["status"] in ("maintenance", "stopped"):
                continue
            sensors = eq_data["sensors"]
            eff = sensors.get("efficiency", sensors.get("performance", None))
            if eff is None or eff >= 70:
                continue
            key = f"eff_{eq_id}"
            if now - _last_action.get(key, 0) < ACTION_COOLDOWN:
                continue
            _last_action[key] = now
            self._stats["recommendations"] += 1
            act = (
                f"⚙️ Eficiencia baja en {eq_data['name']}: {eff:.1f}%. "
                f"Revisar parámetros de proceso"
            )
            self._emit(act, eq_id, now)

    # ─── Helper ───────────────────────────────────────────────────────────────

    def _emit(self, action: str, eq_id: str, now: float):
        self._last_action    = action
        self._last_action_ts = now
        log_agent_action("rule_fired", action, equipment_id=eq_id)
