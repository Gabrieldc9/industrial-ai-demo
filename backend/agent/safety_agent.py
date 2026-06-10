"""
Agente de Seguridad — Prioridad máxima en el sistema de agentes.

Monitorea exclusivamente sensores safety-critical (H2S, temperatura
extrema, flare pilot, vapor pressure). Ante umbral crítico:
  - Crea alerta de mayor severidad
  - Genera WO tipo safety
  - En modo autónomo: puede detener equipos directamente
"""
import time
from cmms.work_orders import create_alert, create_wo, log_agent_action, wo_exists_for_equipment
from simulator.plant import Plant

# Keywords que identifican sensores de seguridad en cualquier industria
SAFETY_KEYWORDS = {"h2s", "ppm", "pilot_temp", "vapor_pressure", "flare_rate", "toxic", "explosive"}

ALERT_COOLDOWN  = 25   # s — más frecuente que maintenance (25s vs 60s)
WO_COOLDOWN     = 150  # s — crear WO safety con cooldown propio
ACTION_COOLDOWN = 20   # s — log de acción autónoma

_last_alert:  dict[str, float] = {}
_last_wo:     dict[str, float] = {}
_last_action: dict[str, float] = {}


class SafetyAgent:

    def __init__(self, plant: Plant, autonomy: dict):
        self.plant    = plant
        self.autonomy = autonomy   # shared con la orquesta {"mode": "assisted"}
        self._last_action     = "Iniciando monitoreo de seguridad..."
        self._last_action_ts  = time.time()
        self._stats = {
            "alerts_generated":    0,
            "safety_wos_created":  0,
            "protocols_activated": 0,
        }

    def get_status(self) -> dict:
        return {
            "id":             "safety",
            "name":           "Agente de Seguridad",
            "icon":           "🛡️",
            "domain":         "H2S · temperatura extrema · gas flare · seguridad de proceso",
            "status":         "active",
            "last_action":    self._last_action,
            "last_action_ts": self._last_action_ts,
            "stats":          dict(self._stats),
        }

    async def run_tick(self):
        snapshot = self.plant.get_snapshot()
        for eq_id, eq_data in snapshot["equipment"].items():
            self._evaluate_safety(eq_id, eq_data)

    def _evaluate_safety(self, eq_id: str, eq_data: dict):
        sensors    = eq_data["sensors"]
        thresholds = eq_data.get("thresholds", {})
        now        = time.time()

        for sensor_key, value in sensors.items():
            if not any(kw in sensor_key.lower() for kw in SAFETY_KEYWORDS):
                continue

            thresh = thresholds.get(sensor_key)
            if not thresh:
                continue

            crit_val  = thresh["critical"]
            warn_val  = thresh["warning"]
            unit      = thresh.get("unit", "")
            low_is_bad = warn_val > crit_val

            is_critical = (low_is_bad and value < crit_val) or (not low_is_bad and value > crit_val)
            is_warning  = not is_critical and (
                (low_is_bad and value < warn_val) or (not low_is_bad and value > warn_val)
            )

            if not (is_critical or is_warning):
                continue

            severity  = "critical" if is_critical else "warning"
            alert_key = f"safety:{eq_id}:{sensor_key}"
            label     = eq_data.get("sensor_names", {}).get(sensor_key, sensor_key)

            # ── Alerta safety (cooldown más corto)
            if now - _last_alert.get(alert_key, 0) >= ALERT_COOLDOWN:
                _last_alert[alert_key] = now
                self._stats["alerts_generated"] += 1
                msg = (
                    f"[SAFETY {severity.upper()}] {eq_data['name']}: "
                    f"{label} = {value:.1f} {unit}"
                )
                create_alert(
                    equipment_id=eq_id,
                    equipment_name=eq_data["name"],
                    sensor=sensor_key,
                    value=value,
                    threshold=crit_val if is_critical else warn_val,
                    severity=severity,
                    message=msg,
                )
                self._last_action    = f"🛡️ {msg}"
                self._last_action_ts = now
                log_agent_action("rule_fired", f"🛡️ {msg}", equipment_id=eq_id)

            if not is_critical:
                continue

            # ── WO safety (solo si no hay una abierta)
            wo_key = f"safety_wo:{eq_id}"
            if (now - _last_wo.get(wo_key, 0) >= WO_COOLDOWN
                    and not wo_exists_for_equipment(eq_id)):
                _last_wo[wo_key] = now
                self._stats["safety_wos_created"] += 1
                wo = create_wo(
                    equipment_id=eq_id,
                    equipment_name=eq_data["name"],
                    title=f"[SAFETY CRÍTICO] {eq_data['name']} — {label} = {value:.1f} {unit}",
                    description=(
                        f"Sensor de seguridad {label} superó umbral crítico. "
                        f"Valor actual: {value:.1f} {unit}. Umbral: {crit_val} {unit}. "
                        f"Activar protocolo de seguridad inmediatamente."
                    ),
                    priority="critical",
                    wo_type="corrective",
                    fault_mode=f"safety_{sensor_key}",
                    sensor_readings=sensors,
                )
                act = f"🚨 Protocolo activado: WO#{wo['wo_number']} — {label} en {eq_data['name']}"
                self._last_action    = act
                self._last_action_ts = time.time()
                self._stats["protocols_activated"] += 1
                log_agent_action("rule_fired", act, equipment_id=eq_id, wo_id=wo["id"])

            # ── Modo autónomo: detener equipo alimentador si H2S crítico en tanque
            mode = self.autonomy.get("mode", "assisted")
            if mode != "autonomous":
                continue

            if "h2s" in sensor_key.lower():
                act_key = f"auto_stop:{eq_id}"
                if now - _last_action.get(act_key, 0) < ACTION_COOLDOWN:
                    continue
                # Detener la bomba de transferencia para evitar llenado del tanque
                pump = self.plant.equipment.get("PUMP-01")
                if pump and pump.status == "running":
                    pump.status = "stopped"
                    _last_action[act_key] = now
                    act = (
                        f"🤖 [AUTÓNOMO] PUMP-01 detenida automáticamente — "
                        f"H2S crítico detectado en {eq_data['name']} ({value:.1f} {unit})"
                    )
                    self._last_action    = act
                    self._last_action_ts = time.time()
                    self._stats["protocols_activated"] += 1
                    log_agent_action("rule_fired", act, equipment_id="PUMP-01")

            elif "pilot_temp" in sensor_key.lower():
                # Pilot del flare apagado → emergencia → alertar en modo autónomo
                act_key = f"auto_flare:{eq_id}"
                if now - _last_action.get(act_key, 0) < ACTION_COOLDOWN:
                    continue
                _last_action[act_key] = now
                act = (
                    f"🤖 [AUTÓNOMO] Alerta crítica: pilot del flare apagado "
                    f"— temperatura {value:.0f}°C. Activar re-ignición de emergencia."
                )
                self._last_action    = act
                self._last_action_ts = time.time()
                log_agent_action("rule_fired", act, equipment_id=eq_id)
