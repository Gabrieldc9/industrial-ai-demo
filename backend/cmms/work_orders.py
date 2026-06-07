"""
CRUD de Work Orders y Alerts.
"""
import time
import json
from .database import get_conn

_wo_counter = [1000]


def _next_wo_number():
    _wo_counter[0] += 1
    return f"WO-{_wo_counter[0]:05d}"


# ─── Work Orders ─────────────────────────────────────────────────────────────

def create_wo(
    equipment_id: str,
    equipment_name: str,
    title: str,
    description: str = "",
    priority: str = "medium",
    wo_type: str = "corrective",
    fault_mode: str = None,
    sensor_readings: dict = None,
    ai_diagnosis: str = None,
    ai_recommendation: str = None,
) -> dict:
    now = time.time()
    wo_number = _next_wo_number()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO work_orders
               (wo_number, equipment_id, equipment_name, title, description,
                priority, type, status, created_at, updated_at,
                fault_mode, sensor_readings, ai_diagnosis, ai_recommendation)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                wo_number, equipment_id, equipment_name, title, description,
                priority, wo_type, "open", now, now,
                fault_mode,
                json.dumps(sensor_readings) if sensor_readings else None,
                ai_diagnosis, ai_recommendation,
            ),
        )
        wo_id = cur.lastrowid
    return get_wo(wo_id)


def get_wo(wo_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM work_orders WHERE id=?", (wo_id,)).fetchone()
        return dict(row) if row else None


def list_wos(limit: int = 50, status: str = None) -> list:
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM work_orders WHERE status=? ORDER BY created_at DESC LIMIT ?",
                (status, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM work_orders ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


def update_wo_status(wo_id: int, status: str, notes: str = None) -> dict:
    now = time.time()
    completed_at = now if status == "completed" else None
    with get_conn() as conn:
        conn.execute(
            "UPDATE work_orders SET status=?, updated_at=?, completed_at=? WHERE id=?",
            (status, now, completed_at, wo_id)
        )
    return get_wo(wo_id)


def update_wo_diagnosis(wo_id: int, ai_diagnosis: str, ai_recommendation: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE work_orders SET ai_diagnosis=?, ai_recommendation=?, updated_at=? WHERE id=?",
            (ai_diagnosis, ai_recommendation, time.time(), wo_id)
        )


def wo_exists_for_equipment(equipment_id: str) -> bool:
    """Evita WOs duplicadas para el mismo equipo con status open/in_progress."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM work_orders WHERE equipment_id=? AND status IN ('open','in_progress') LIMIT 1",
            (equipment_id,)
        ).fetchone()
        return row is not None


# ─── Alerts ──────────────────────────────────────────────────────────────────

def create_alert(
    equipment_id: str,
    equipment_name: str,
    sensor: str,
    value: float,
    threshold: float,
    severity: str,
    message: str = None,
    wo_id: int = None,
) -> dict:
    now = time.time()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO alerts
               (equipment_id, equipment_name, sensor, value, threshold, severity, message, created_at, wo_id)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (equipment_id, equipment_name, sensor, value, threshold, severity, message, now, wo_id)
        )
        return {"id": cur.lastrowid, "equipment_id": equipment_id, "sensor": sensor,
                "value": value, "severity": severity, "message": message, "created_at": now}


def list_alerts(limit: int = 50, unacknowledged_only: bool = False) -> list:
    with get_conn() as conn:
        if unacknowledged_only:
            rows = conn.execute(
                "SELECT * FROM alerts WHERE acknowledged=0 ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


def acknowledge_alert(alert_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE alerts SET acknowledged=1 WHERE id=?", (alert_id,))


# ─── Maintenance Log ──────────────────────────────────────────────────────────

def log_maintenance(equipment_id: str, wo_id: int, action: str,
                    health_before: float, health_after: float, notes: str = None):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO maintenance_log
               (equipment_id, wo_id, action, health_before, health_after, performed_at, notes)
               VALUES (?,?,?,?,?,?,?)""",
            (equipment_id, wo_id, action, health_before, health_after, time.time(), notes)
        )


def list_maintenance_log(limit: int = 30) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM maintenance_log ORDER BY performed_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ─── Agent Log ───────────────────────────────────────────────────────────────

def log_agent_action(action_type: str, summary: str, detail: str = None,
                     equipment_id: str = None, wo_id: int = None):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO agent_log
               (timestamp, equipment_id, action_type, summary, detail, wo_id)
               VALUES (?,?,?,?,?,?)""",
            (time.time(), equipment_id, action_type, summary, detail, wo_id)
        )


def list_agent_log(limit: int = 50) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM agent_log ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
