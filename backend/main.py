"""
Servidor principal — FastAPI + WebSockets + REST CMMS.
Sirve el frontend React compilado desde /static.
"""
import sys
import os
# Fix encoding en Windows antes que cualquier otra cosa
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Cargar .env si existe
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(os.path.abspath(_env_path))
except ImportError:
    pass
import asyncio
import time
import json

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager

from cmms.database import init_db
from cmms.work_orders import (
    list_wos, get_wo, update_wo_status,
    list_alerts, acknowledge_alert,
    list_maintenance_log, list_agent_log,
    log_agent_action,
)
from simulator.plant import Plant
from agent.maintenance_agent import MaintenanceAgent

# ─── Estado global ────────────────────────────────────────────────────────────

plant = Plant()
agent = MaintenanceAgent(plant)
connected_clients: list[WebSocket] = []

TICK_INTERVAL = 2.0       # segundos entre ticks de simulación
AGENT_INTERVAL = 5.0      # segundos entre evaluaciones del agente
BROADCAST_INTERVAL = 1.0  # segundos entre broadcasts a clientes

# Control de velocidad de simulación (1x = normal, 5x = rápido para demo)
sim_speed = {"multiplier": 1.0}
sim_paused = {"value": False}


# ─── Background loops ─────────────────────────────────────────────────────────

async def simulation_loop():
    """Tick del simulador de planta."""
    while True:
        if not sim_paused["value"]:
            dt = TICK_INTERVAL * sim_speed["multiplier"]
            plant.tick(dt=dt)
        await asyncio.sleep(TICK_INTERVAL)


async def agent_loop():
    """Ciclo del agente autónomo."""
    await asyncio.sleep(5)  # dejar que la planta arranque
    while True:
        try:
            await agent.run_tick()
        except Exception as e:
            print(f"[AGENT ERROR] {e}")
        await asyncio.sleep(AGENT_INTERVAL)


async def broadcast_loop():
    """Broadcast de datos en tiempo real a todos los clientes WS conectados."""
    while True:
        if connected_clients:
            snapshot = plant.get_snapshot()
            payload = json.dumps({"type": "plant_update", "data": snapshot})
            dead = []
            for ws in connected_clients:
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                connected_clients.remove(ws)
        await asyncio.sleep(BROADCAST_INTERVAL)


# ─── App lifecycle ────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    log_agent_action("rule_fired", "Sistema iniciado. Planta virtual online.")
    asyncio.create_task(simulation_loop())
    asyncio.create_task(agent_loop())
    asyncio.create_task(broadcast_loop())
    yield


app = FastAPI(title="Industrial Demo", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    try:
        # Enviar snapshot inmediato al conectar
        snapshot = plant.get_snapshot()
        await ws.send_text(json.dumps({"type": "plant_update", "data": snapshot}))
        while True:
            await ws.receive_text()  # mantener conexión viva
    except WebSocketDisconnect:
        if ws in connected_clients:
            connected_clients.remove(ws)


# ─── REST — Plant ─────────────────────────────────────────────────────────────

@app.get("/api/plant/snapshot")
def get_snapshot():
    return plant.get_snapshot()


@app.get("/api/plant/equipment/{eq_id}")
def get_equipment(eq_id: str):
    eq = plant.equipment.get(eq_id)
    if not eq:
        raise HTTPException(404, "Equipment not found")
    return eq.to_dict()


class MaintenanceRequest(BaseModel):
    equipment_id: str


@app.post("/api/plant/maintenance")
def trigger_maintenance(req: MaintenanceRequest):
    """Trigger manual de mantenimiento desde el panel."""
    eq = plant.equipment.get(req.equipment_id)
    if not eq:
        raise HTTPException(404, "Equipment not found")
    health_before, health_after = eq.perform_maintenance()
    from cmms.work_orders import list_wos, log_maintenance
    open_wos = [w for w in list_wos(status="open") if w["equipment_id"] == req.equipment_id]
    wo_id = None
    if open_wos:
        update_wo_status(open_wos[0]["id"], "completed")
        wo_id = open_wos[0]["id"]
    log_maintenance(req.equipment_id, wo_id, "manual_maintenance", health_before, health_after, "Intervención manual desde panel")
    log_agent_action("maintenance_triggered", f"Mantenimiento manual en {eq.name}: {health_before:.1f}% → {health_after:.1f}%", equipment_id=req.equipment_id)
    return {"ok": True, "health_before": health_before, "health_after": health_after}


class FaultRequest(BaseModel):
    equipment_id: str
    fault_mode: str = "bearing_wear"


@app.post("/api/plant/inject-fault")
def inject_fault(req: FaultRequest):
    """Inyectar falla manualmente para demo."""
    eq = plant.equipment.get(req.equipment_id)
    if not eq:
        raise HTTPException(404, "Equipment not found")
    eq.fault_mode = req.fault_mode
    eq.degradation_rate *= 5
    log_agent_action("rule_fired", f"Falla inyectada manualmente en {eq.name}: {req.fault_mode}", equipment_id=req.equipment_id)
    return {"ok": True}


class SpeedRequest(BaseModel):
    multiplier: float   # 0.5 | 1 | 2 | 5 | 10


@app.post("/api/plant/speed")
def set_speed(req: SpeedRequest):
    """Controlar velocidad de simulación para demo."""
    m = max(0.1, min(20.0, req.multiplier))
    sim_speed["multiplier"] = m
    log_agent_action("rule_fired", f"Velocidad de simulación → {m}x")
    return {"ok": True, "multiplier": m}


@app.post("/api/plant/pause")
def toggle_pause():
    """Pausar/reanudar simulación."""
    sim_paused["value"] = not sim_paused["value"]
    state = "pausada" if sim_paused["value"] else "reanudada"
    log_agent_action("rule_fired", f"Simulación {state}")
    return {"ok": True, "paused": sim_paused["value"]}


@app.post("/api/plant/reset")
def reset_plant():
    """Resetear toda la planta al estado inicial."""
    global plant, agent
    plant = Plant()
    agent = MaintenanceAgent(plant)
    # Limpiar DB
    from cmms.database import get_conn
    with get_conn() as conn:
        conn.execute("DELETE FROM work_orders")
        conn.execute("DELETE FROM alerts")
        conn.execute("DELETE FROM maintenance_log")
        conn.execute("DELETE FROM agent_log")
    log_agent_action("rule_fired", "Planta reseteada a estado inicial")
    return {"ok": True}


@app.post("/api/demo/scenario/{name}")
async def run_demo_scenario(name: str):
    """
    Escenarios predefinidos para demo en vivo.
    - cascade: falla en cascada (pump → motor → compressor)
    - critical: llevar todos los equipos a estado crítico rápido
    - recovery: ejecutar mantenimiento en todos y volver a verde
    """
    if name == "cascade":
        import asyncio
        sequence = [
            ("PUMP-01",  "bearing_wear"),
            ("MOTOR-01", "overload"),
            ("COMP-01",  "valve_wear"),
        ]
        for eq_id, fault in sequence:
            eq = plant.equipment.get(eq_id)
            if eq:
                eq.fault_mode = fault
                eq.degradation_rate *= 8
                eq.health = max(30, eq.health - 20)
        log_agent_action("rule_fired", "Escenario CASCADA activado: falla progresiva en 3 equipos")
        return {"ok": True, "scenario": "cascade", "affected": [e[0] for e in sequence]}

    elif name == "critical":
        for eq in plant.equipment.values():
            eq.health = 22
            eq.degradation_rate = 0.5
            if not eq.fault_mode:
                eq._inject_fault()
        log_agent_action("rule_fired", "Escenario CRÍTICO activado: todos los equipos en falla")
        return {"ok": True, "scenario": "critical"}

    elif name == "recovery":
        results = []
        for eq in plant.equipment.values():
            if eq.health < 80:
                hb, ha = eq.perform_maintenance()
                results.append({"id": eq.id, "before": round(hb, 1), "after": round(ha, 1)})
        log_agent_action("rule_fired", f"Escenario RECOVERY: {len(results)} equipos mantenidos")
        return {"ok": True, "scenario": "recovery", "maintained": results}

    raise HTTPException(400, f"Escenario desconocido: {name}. Usar: cascade | critical | recovery")


@app.get("/api/plant/status")
def get_plant_status():
    """Estado resumido de la planta + velocidad actual."""
    return {
        **plant.get_snapshot(),
        "sim_speed": sim_speed["multiplier"],
        "sim_paused": sim_paused["value"],
    }


# ─── REST — CMMS ──────────────────────────────────────────────────────────────

@app.get("/api/work-orders")
def get_work_orders(status: str = None, limit: int = 50):
    return list_wos(limit=limit, status=status)


@app.get("/api/work-orders/{wo_id}")
def get_work_order(wo_id: int):
    wo = get_wo(wo_id)
    if not wo:
        raise HTTPException(404, "WO not found")
    return wo


class WOStatusUpdate(BaseModel):
    status: str


@app.patch("/api/work-orders/{wo_id}/status")
def patch_wo_status(wo_id: int, body: WOStatusUpdate):
    return update_wo_status(wo_id, body.status)


@app.get("/api/alerts")
def get_alerts(unacknowledged_only: bool = False, limit: int = 50):
    return list_alerts(limit=limit, unacknowledged_only=unacknowledged_only)


@app.post("/api/alerts/{alert_id}/acknowledge")
def ack_alert(alert_id: int):
    acknowledge_alert(alert_id)
    return {"ok": True}


@app.get("/api/maintenance-log")
def get_maintenance_log(limit: int = 30):
    return list_maintenance_log(limit=limit)


@app.get("/api/agent-log")
def get_agent_log(limit: int = 50):
    return list_agent_log(limit=limit)


@app.get("/api/stats")
def get_stats():
    snapshot = plant.get_snapshot()
    wos = list_wos(limit=200)
    return {
        "plant_health": snapshot["plant_health"],
        "active_faults": len(snapshot["active_faults"]),
        "equipment_status": {
            status: sum(1 for e in snapshot["equipment"].values() if e["status"] == status)
            for status in ("running", "warning", "critical", "maintenance", "stopped")
        },
        "wo_summary": {
            status: sum(1 for w in wos if w["status"] == status)
            for status in ("open", "in_progress", "completed", "cancelled")
        },
        "connected_clients": len(connected_clients),
    }


# ─── Frontend (React build) ───────────────────────────────────────────────────

# Local: frontend/dist  — Railway: backend/frontend_dist
_candidates = [
    os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"),
    os.path.join(os.path.dirname(__file__), "frontend_dist"),
]
STATIC_DIR = next((os.path.abspath(p) for p in _candidates if os.path.isdir(p)), None) or ""
if os.path.exists(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/")
    async def serve_root():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
else:
    @app.get("/")
    def root():
        return {"status": "ok", "message": "Backend running. Build frontend to see dashboard."}
