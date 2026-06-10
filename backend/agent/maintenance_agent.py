"""
Agente autónomo de mantenimiento — híbrido (reglas + Claude).

Flujo por tick:
  1. Reglas rápidas: detectar umbrales cruzados → generar alerta + WO básica
  2. Claude (async): para fallas activas, diagnosticar y enriquecer la WO
  3. Decisión de mantenimiento: si equipo crítico → triggerear mantenimiento
"""
import os
import sys
import time
import json
import asyncio
from typing import Optional

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from groq import Groq

from cmms.work_orders import (
    create_wo, update_wo_status, update_wo_diagnosis,
    create_alert, log_maintenance, log_agent_action,
    wo_exists_for_equipment,
)
from simulator.plant import Plant

# ─── Config ──────────────────────────────────────────────────────────────────

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
AI_MODEL = "llama-3.1-8b-instant"   # Llama 3.1 via Groq: gratuito y ultra-rápido

# Cuántos ticks entre diagnósticos Claude (evitar spam de tokens)
CLAUDE_DIAGNOSIS_COOLDOWN = 30   # segundos
MAINTENANCE_TRIGGER_HEALTH = 25  # health < 25% → mantenimiento inmediato
ALERT_COOLDOWN = 60              # segundos entre alertas del mismo equipo+sensor
WO_LOG_COOLDOWN = 60             # segundos entre entradas de agente para mismo equipo

_last_claude_call: dict[str, float] = {}         # equipment_id → timestamp
_last_alert: dict[str, float] = {}               # "equipment_id:sensor" → timestamp
_last_agent_log: dict[str, float] = {}           # equipment_id → timestamp


# ─── Agente principal ─────────────────────────────────────────────────────────

class MaintenanceAgent:

    def __init__(self, plant: Plant):
        self.plant = plant
        self.client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
        self._pending_diagnoses: list[dict] = []   # WOs en cola para diagnóstico IA
        self._maintenance_queue: list[str] = []     # equipment_ids a mantener

    async def run_tick(self):
        """Ejecutar un ciclo del agente. Llamado desde el loop principal."""
        snapshot = self.plant.get_snapshot()

        for eq_id, eq_data in snapshot["equipment"].items():
            await self._evaluate_equipment(eq_id, eq_data)

        # Procesar diagnósticos pendientes con Claude
        if self._pending_diagnoses and self.client:
            to_diagnose = self._pending_diagnoses.copy()
            self._pending_diagnoses.clear()
            for item in to_diagnose:
                await self._run_claude_diagnosis(item)

        # Ejecutar mantenimientos en cola
        while self._maintenance_queue:
            eq_id = self._maintenance_queue.pop(0)
            self._execute_maintenance(eq_id)

    async def _evaluate_equipment(self, eq_id: str, eq_data: dict):
        status = eq_data["status"]
        health = eq_data["health"]
        sensors = eq_data["sensors"]
        fault_mode = eq_data.get("fault_mode")

        # ── Regla 1: mantenimiento inmediato si health crítico
        if health < MAINTENANCE_TRIGGER_HEALTH and eq_id not in self._maintenance_queue:
            if status not in ("maintenance", "stopped"):
                self._maintenance_queue.append(eq_id)
                log_agent_action(
                    "maintenance_triggered",
                    f"Health crítico en {eq_data['name']} ({health:.1f}%) → mantenimiento programado",
                    equipment_id=eq_id,
                )
            return

        # ── Regla 2: detectar umbrales de sensores (con cooldown anti-spam)
        severity = self._check_thresholds(sensors, eq_data["thresholds"])
        if severity:
            top_sensor, top_value, top_thresh = severity
            alert_key = f"{eq_id}:{top_sensor}"
            now = time.time()

            # Solo crear alerta si pasó el cooldown
            if now - _last_alert.get(alert_key, 0) >= ALERT_COOLDOWN:
                _last_alert[alert_key] = now
                create_alert(
                    equipment_id=eq_id,
                    equipment_name=eq_data["name"],
                    sensor=top_sensor,
                    value=top_value,
                    threshold=top_thresh,
                    severity=status,
                    message=f"{top_sensor.capitalize()} = {top_value:.1f} (umbral: {top_thresh})",
                )

            # Log del agente también con cooldown
            if now - _last_agent_log.get(eq_id, 0) >= WO_LOG_COOLDOWN:
                _last_agent_log[eq_id] = now
                log_agent_action(
                    "alert_detected",
                    f"Alerta {status.upper()} en {eq_data['name']}: {top_sensor} = {top_value:.1f}",
                    equipment_id=eq_id,
                )

            # ── Regla 3: crear WO si no existe una abierta para este equipo
            if not wo_exists_for_equipment(eq_id):
                priority = "critical" if status == "critical" else "high"
                wo_type = "predictive" if fault_mode else "corrective"
                title = (
                    f"[{priority.upper()}] {eq_data['name']} — {fault_mode or top_sensor + ' fuera de rango'}"
                )
                wo = create_wo(
                    equipment_id=eq_id,
                    equipment_name=eq_data["name"],
                    title=title,
                    description=f"Sensor {top_sensor} = {top_value:.1f} supera umbral {top_thresh}.",
                    priority=priority,
                    wo_type=wo_type,
                    fault_mode=fault_mode,
                    sensor_readings=sensors,
                )
                log_agent_action(
                    "wo_created",
                    f"WO creada: {wo['wo_number']} para {eq_data['name']}",
                    equipment_id=eq_id,
                    wo_id=wo["id"],
                )

                # Encolar diagnóstico Claude si no recibió uno reciente
                last = _last_claude_call.get(eq_id, 0)
                if time.time() - last > CLAUDE_DIAGNOSIS_COOLDOWN:
                    self._pending_diagnoses.append({
                        "wo_id": wo["id"],
                        "eq_id": eq_id,
                        "eq_data": eq_data,
                    })

    def _check_thresholds(self, sensors: dict, thresholds: dict):
        """
        Retorna (sensor, value, threshold) del sensor más crítico, o None.
        Dirección inferida de los umbrales: warning > critical → bajo es malo.
        """
        worst = None
        worst_ratio = 0

        for sensor, value in sensors.items():
            thresh = thresholds.get(sensor)
            if not thresh:
                continue
            crit = thresh["critical"]
            warn = thresh["warning"]
            low_is_bad = warn > crit   # dirección data-driven, no hardcodeada

            if low_is_bad:
                if value < crit:
                    ratio = (crit - value) / max(crit, 0.001) + 1
                    if ratio > worst_ratio:
                        worst_ratio = ratio
                        worst = (sensor, value, crit)
                elif value < warn:
                    ratio = (warn - value) / max(warn, 0.001)
                    if ratio > worst_ratio:
                        worst_ratio = ratio
                        worst = (sensor, value, warn)
            else:
                if value > crit:
                    ratio = value / max(crit, 0.001)
                    if ratio > worst_ratio:
                        worst_ratio = ratio
                        worst = (sensor, value, crit)
                elif value > warn:
                    ratio = value / max(warn, 0.001)
                    if ratio > worst_ratio:
                        worst_ratio = ratio
                        worst = (sensor, value, warn)

        return worst  # (sensor, value, threshold) o None

    async def _run_claude_diagnosis(self, item: dict):
        """Llamar a Claude para diagnóstico detallado de una falla."""
        eq_data = item["eq_data"]
        wo_id = item["wo_id"]
        eq_id = item["eq_id"]
        _last_claude_call[eq_id] = time.time()

        sensors_str = "\n".join(
            f"  - {k}: {v:.2f} {eq_data.get('sensor_units', {}).get(k, '')}"
            for k, v in eq_data["sensors"].items()
        )
        thresholds_str = "\n".join(
            f"  - {k}: warning={v['warning']}, critical={v['critical']} {v['unit']}"
            for k, v in eq_data.get("thresholds", {}).items()
        )

        prompt = f"""Sos un ingeniero experto en mantenimiento industrial. Analizá la siguiente situación:

EQUIPO: {eq_data['name']} (ID: {eq_data['id']}, tipo: {eq_data['type']})
HEALTH: {eq_data['health']:.1f}%
ESTADO: {eq_data['status']}
MODO DE FALLA DETECTADO: {eq_data.get('fault_mode') or 'No identificado aún'}
HORAS OPERATIVAS: {eq_data['operating_hours']:.1f}h

LECTURAS DE SENSORES:
{sensors_str}

UMBRALES DE REFERENCIA:
{thresholds_str}

Respondé en JSON con este formato exacto:
{{
  "diagnosis": "Descripción técnica de la falla en 2-3 oraciones",
  "root_cause": "Causa raíz probable",
  "urgency": "immediate|24h|week",
  "recommended_actions": ["acción 1", "acción 2", "acción 3"],
  "spare_parts": ["repuesto 1", "repuesto 2"],
  "estimated_downtime_hours": 4
}}"""

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=AI_MODEL,
                    max_tokens=600,
                    messages=[{"role": "user", "content": prompt}]
                )
            )
            raw = response.choices[0].message.content.strip()
            # Extraer JSON si viene envuelto en markdown
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)

            diagnosis = data.get("diagnosis", "")
            actions = data.get("recommended_actions", [])
            recommendation = (
                f"Urgencia: {data.get('urgency', 'N/A')} | "
                f"Causa raíz: {data.get('root_cause', '')} | "
                f"Downtime estimado: {data.get('estimated_downtime_hours', '?')}h | "
                f"Acciones: {'; '.join(actions)} | "
                f"Repuestos: {', '.join(data.get('spare_parts', []))}"
            )
            update_wo_diagnosis(wo_id, diagnosis, recommendation)
            log_agent_action(
                "diagnosis",
                f"Diagnóstico IA completado para WO#{wo_id}: {diagnosis[:80]}...",
                equipment_id=eq_id,
                wo_id=wo_id,
                detail=json.dumps(data, ensure_ascii=False),
            )
        except Exception as e:
            log_agent_action(
                "diagnosis",
                f"Error en diagnóstico IA para WO#{wo_id}: {str(e)[:100]}",
                equipment_id=eq_id,
                wo_id=wo_id,
            )

    def _execute_maintenance(self, eq_id: str):
        """Simula intervención de mantenimiento en el equipo."""
        eq = self.plant.equipment.get(eq_id)
        if not eq:
            return
        health_before, health_after = eq.perform_maintenance()

        # Completar WO abierta si existe
        from cmms.work_orders import list_wos
        open_wos = [w for w in list_wos(status="open") if w["equipment_id"] == eq_id]
        wo_id = None
        if open_wos:
            wo = open_wos[0]
            update_wo_status(wo["id"], "completed")
            wo_id = wo["id"]

        log_maintenance(
            equipment_id=eq_id,
            wo_id=wo_id,
            action="maintenance_performed",
            health_before=health_before,
            health_after=health_after,
            notes="Intervención automática por health crítico",
        )
        log_agent_action(
            "maintenance_triggered",
            f"Mantenimiento ejecutado en {eq.name}: health {health_before:.1f}% → {health_after:.1f}%",
            equipment_id=eq_id,
            wo_id=wo_id,
        )
