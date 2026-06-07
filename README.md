# 🏭 Industrial AI Demo

> Planta industrial virtual con simulación de sensores, fallas, Work Orders y un **agente autónomo de mantenimiento** impulsado por Claude AI — todo en tiempo real.

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template)

---

## ✨ Qué hace

| Módulo | Descripción |
|--------|-------------|
| **Simulador de Planta** | 6 equipos (bomba, compresor, cinta, motor, intercambiador, válvula) con degradación física realista |
| **Motor de Fallas** | 9 modos: bearing wear, seal leak, cavitation, overload, misalignment, fouling... |
| **CMMS** | Work Orders con prioridad, diagnóstico IA, recomendaciones y estado |
| **Agente Híbrido** | Reglas rápidas (umbral → alerta → WO) + Claude AI para diagnóstico detallado |
| **Streaming Live** | WebSocket push cada segundo a todos los clientes conectados |
| **Dashboard React** | Sensores en tiempo real, sparklines, controles de demo, historial de mantenimiento |

## 🎮 Controles de Demo

- **Velocidad**: 0.5× — 1× — 2× — 5× — 10× (acelerar la simulación para demos)
- **Escenario Cascada**: falla progresiva en bomba → motor → compresor
- **Escenario Crisis Total**: todos los equipos en estado crítico simultáneamente  
- **Escenario Recovery**: mantenimiento masivo, volver a verde
- **Inyección manual**: elegir equipo y modo de falla específico
- **Reset**: reiniciar planta y limpiar DB

## 🚀 Inicio rápido (local)

```bash
# 1. Clonar
git clone https://github.com/Gabrieldc9/industrial-ai-demo.git
cd industrial-ai-demo

# 2. Configurar
cp .env.example .env
# Editar .env → agregar ANTHROPIC_API_KEY

# 3. Construir frontend (primera vez)
build-frontend.bat

# 4. Iniciar
start-dev.bat
# → http://localhost:8000
```

### Requisitos
- Python 3.11+
- Node.js 18+
- `pip install -r backend/requirements.txt`

## ☁️ Deploy a Railway

1. Fork este repo
2. Railway → **New Project** → Deploy from GitHub → elegir `industrial-ai-demo`
3. Agregar variable de entorno: `ANTHROPIC_API_KEY=sk-ant-...`
4. Railway hace el build automático (nixpacks.toml) y asigna URL pública

## 🗂️ Estructura

```
industrial-ai-demo/
├── backend/
│   ├── main.py              # FastAPI + WebSocket server
│   ├── simulator/
│   │   └── plant.py         # 6 equipos, sensores, degradación, fallas
│   ├── cmms/
│   │   ├── database.py      # SQLite init
│   │   └── work_orders.py   # CRUD WOs, alertas, logs
│   ├── agent/
│   │   └── maintenance_agent.py  # Reglas + Claude AI
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx
│       └── components/
│           ├── EquipmentCard.jsx   # Card por equipo con sparklines
│           ├── WorkOrderPanel.jsx  # CMMS panel
│           ├── DemoControls.jsx    # Velocidad + escenarios + reset
│           ├── AlertsPanel.jsx     # Alertas con acknowledge
│           ├── AgentLog.jsx        # Log en tiempo real del agente
│           └── MaintenanceHistory.jsx
├── nixpacks.toml    # Build config para Railway
├── railway.toml     # Deploy config
└── start-dev.bat    # Script de inicio Windows
```

## 🔌 API REST

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/plant/snapshot` | GET | Estado completo de la planta |
| `/api/plant/inject-fault` | POST | Inyectar falla en un equipo |
| `/api/plant/maintenance` | POST | Ejecutar mantenimiento manual |
| `/api/plant/speed` | POST | Cambiar velocidad (0.1× — 20×) |
| `/api/plant/pause` | POST | Pausar/reanudar simulación |
| `/api/plant/reset` | POST | Resetear planta y DB |
| `/api/demo/scenario/{name}` | POST | cascade \| critical \| recovery |
| `/api/work-orders` | GET | Listar WOs (filtro por status) |
| `/api/alerts` | GET | Alertas (con filtro unacknowledged) |
| `/api/agent-log` | GET | Log de actividad del agente |
| `/api/stats` | GET | KPIs resumidos |
| `/ws` | WS | Stream tiempo real |

## 🤖 Agente de Mantenimiento

El agente es **híbrido**:

1. **Reglas (cada 5s)**: detecta umbrales cruzados → genera alerta → crea WO si no existe
2. **Claude AI (async)**: cuando se detecta una falla, Claude diagnostica root cause, urgencia, acciones recomendadas y repuestos necesarios — enriquece la WO automáticamente
3. **Auto-mantenimiento**: si health < 25% → ejecuta intervención, resetea degradación, cierra WO

### Cooldowns anti-spam
- Alertas: mínimo 60s entre alertas del mismo sensor en el mismo equipo
- Log del agente: mínimo 15s entre entradas del mismo equipo

## 📊 Modelo de Simulación

### Equipos y sensores
| Equipo | Sensores |
|--------|---------|
| Bomba | temperatura, vibración, presión, flujo, corriente |
| Compresor | temperatura, vibración, presión, corriente, eficiencia |
| Cinta | temperatura, vibración, corriente, eficiencia |
| Motor | temperatura, vibración, corriente |
| Intercambiador | temperatura, presión, flujo, eficiencia |
| Válvula | presión, flujo |

### Modos de falla por equipo
- **Bomba**: bearing_wear, seal_leak, cavitation
- **Compresor**: bearing_wear, overload, valve_wear
- **Cinta**: bearing_wear, misalignment, belt_slip
- **Motor**: overload, bearing_wear, insulation_degradation
- **Intercambiador**: fouling, seal_leak
- **Válvula**: seal_leak, actuator_fault

---

Construido con [Claude Code](https://claude.ai/code) · FastAPI · React · Recharts · TailwindCSS · SQLite
