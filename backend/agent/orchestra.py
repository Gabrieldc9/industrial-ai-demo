"""
Orquesta de agentes — coordina todos los agentes del sistema.

Reemplaza al MaintenanceAgent solitario como punto de entrada del loop.
Cada agente tiene su dominio y corre en paralelo.
La orquesta provee la vista unificada del "cerebro de la planta".
"""
import asyncio
from simulator.plant import Plant
from agent.maintenance_agent import MaintenanceAgent
from agent.safety_agent import SafetyAgent
from agent.process_agent import ProcessAgent

AUTONOMY_MODES = {
    "manual":     "Solo observa. Sin acciones automáticas.",
    "assisted":   "Crea WOs y alertas. El humano ejecuta.",
    "autonomous": "Actúa solo. El humano supervisa.",
}

# Agentes ordenados por prioridad de display
AGENT_ORDER = ["safety", "maintenance", "process"]


class AgentOrchestra:

    def __init__(self, plant: Plant):
        self.plant    = plant
        self.autonomy = {"mode": "assisted"}
        self._agents  = self._build_agents()

    def _build_agents(self) -> list:
        return [
            SafetyAgent(self.plant, self.autonomy),
            MaintenanceAgent(self.plant),
            ProcessAgent(self.plant, self.autonomy),
        ]

    def set_plant(self, new_plant: Plant):
        """Reemplazar referencia de planta (reset de industria o reset general)."""
        self.plant = new_plant
        self._agents = self._build_agents()

    def set_autonomy_mode(self, mode: str):
        if mode not in AUTONOMY_MODES:
            raise ValueError(
                f"Modo inválido: '{mode}'. Válidos: {list(AUTONOMY_MODES.keys())}"
            )
        self.autonomy["mode"] = mode

    async def run_tick(self):
        """Ejecutar todos los agentes en paralelo. Errores aislados por agente."""
        results = await asyncio.gather(
            *[agent.run_tick() for agent in self._agents],
            return_exceptions=True,
        )
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                agent_name = getattr(self._agents[i], '__class__', {__name__: '?'}).__name__
                print(f"[ORCHESTRA ERROR] {agent_name}: {r}")

    def get_status(self) -> dict:
        agents_status = []
        for agent in self._agents:
            if hasattr(agent, "get_status"):
                agents_status.append(agent.get_status())
            else:
                agents_status.append({
                    "id":             "unknown",
                    "name":           type(agent).__name__,
                    "icon":           "🤖",
                    "domain":         "—",
                    "status":         "active",
                    "last_action":    "—",
                    "last_action_ts": 0,
                    "stats":          {},
                })

        # Ordenar por AGENT_ORDER
        order_map = {aid: i for i, aid in enumerate(AGENT_ORDER)}
        agents_status.sort(key=lambda a: order_map.get(a["id"], 99))

        return {
            "agents":               agents_status,
            "autonomy_mode":        self.autonomy["mode"],
            "autonomy_description": AUTONOMY_MODES[self.autonomy["mode"]],
        }
