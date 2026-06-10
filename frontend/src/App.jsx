import { useState, useEffect, useRef } from 'react'
import { Factory, Wifi, WifiOff, LayoutDashboard, ClipboardList, Bell, History, Bot } from 'lucide-react'
import { useWebSocket } from './hooks/useWebSocket'
import { KPIBar } from './components/KPIBar'
import { EquipmentCard } from './components/EquipmentCard'
import { WorkOrderPanel } from './components/WorkOrderPanel'
import { AgentLog } from './components/AgentLog'
import { DemoControls } from './components/DemoControls'
import { AlertsPanel } from './components/AlertsPanel'
import { MaintenanceHistory } from './components/MaintenanceHistory'
import { PinGuardProvider, usePinGuard } from './context/PinGuard'
import { IndustrySelector } from './components/IndustrySelector'

const HISTORY_SIZE = 80

const TABS = [
  { id: 'overview', label: 'Planta', icon: <LayoutDashboard size={14} /> },
  { id: 'workorders', label: 'Órdenes', icon: <ClipboardList size={14} /> },
  { id: 'alerts', label: 'Alertas', icon: <Bell size={14} /> },
  { id: 'history', label: 'Historial', icon: <History size={14} /> },
  { id: 'agent', label: 'Agente IA', icon: <Bot size={14} /> },
]

// AppInner accede al contexto PinGuard; App lo envuelve con el provider.
function AppInner() {
  const { protectedFetch } = usePinGuard()
  const { plantData, connected } = useWebSocket()
  const historyRef = useRef({})
  const [history, setHistory] = useState({})
  const [toastMsg, setToastMsg] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [unackedAlerts, setUnackedAlerts] = useState(0)
  const [showIndustrySelector, setShowIndustrySelector] = useState(false)

  // Acumular historial de sensores
  useEffect(() => {
    if (!plantData) return
    const newHistory = { ...historyRef.current }
    for (const [eqId, eq] of Object.entries(plantData.equipment)) {
      if (!newHistory[eqId]) newHistory[eqId] = []
      newHistory[eqId] = [...newHistory[eqId].slice(-(HISTORY_SIZE - 1)), eq.sensors]
    }
    historyRef.current = newHistory
    setHistory({ ...newHistory })
  }, [plantData])

  // Polling de alertas no leídas para el badge
  useEffect(() => {
    const fetchUnacked = async () => {
      const res = await fetch('/api/alerts?unacknowledged_only=true&limit=1')
      if (res.ok) {
        const data = await res.json()
        // Contar con endpoint stats
        const s = await fetch('/api/stats')
        if (s.ok) {
          const stats = await s.json()
          // Las alertas están en la DB; usamos length del primer fetch
        }
      }
    }
    const id = setInterval(async () => {
      const res = await fetch('/api/alerts?unacknowledged_only=true&limit=100')
      if (res.ok) {
        const data = await res.json()
        setUnackedAlerts(data.length)
      }
    }, 5000)
    return () => clearInterval(id)
  }, [])

  function showToast(msg) {
    setToastMsg(msg)
    setTimeout(() => setToastMsg(null), 4000)
  }

  async function handleMaintenance(eqId) {
    const res = await protectedFetch('/api/plant/maintenance', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ equipment_id: eqId }),
    })
    if (res?.ok) {
      const data = await res.json()
      showToast(`✅ Mantenimiento en ${eqId}: ${data.health_before.toFixed(0)}% → ${data.health_after.toFixed(0)}%`)
    }
  }

  async function handleInjectFault(eqId) {
    const faults = ['bearing_wear', 'seal_leak', 'overload', 'misalignment', 'cavitation']
    const fault = faults[Math.floor(Math.random() * faults.length)]
    const res = await protectedFetch('/api/plant/inject-fault', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ equipment_id: eqId, fault_mode: fault }),
    })
    if (res?.ok) showToast(`⚡ Falla inyectada: ${fault} en ${eqId}`)
  }

  const equipment = plantData?.equipment ? Object.values(plantData.equipment) : []

  const criticalCount = equipment.filter(e => e.status === 'critical').length
  const warningCount = equipment.filter(e => e.status === 'warning').length

  return (
    <div className="min-h-screen bg-[#0a0f1e] text-slate-200 flex flex-col">
      {/* Toast */}
      {toastMsg && (
        <div className="fixed top-4 right-4 z-50 bg-slate-800 border border-slate-600 rounded-lg px-4 py-3 text-sm shadow-2xl max-w-sm">
          {toastMsg}
        </div>
      )}

      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40 shrink-0">
        <div className="max-w-screen-2xl mx-auto px-4 py-2.5 flex items-center gap-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-brand-500/20 border border-brand-500/30 flex items-center justify-center">
              <Factory size={16} className="text-brand-500" />
            </div>
            <div>
              <h1 className="font-bold text-white text-sm leading-none">Industrial AI Demo</h1>
              <p className="text-[10px] text-slate-500">Mantenimiento Predictivo Autónomo</p>
            </div>
          </div>

          {/* Status críticos inline */}
          <div className="hidden md:flex items-center gap-3 ml-4">
            {criticalCount > 0 && (
              <span className="flex items-center gap-1.5 text-xs text-red-400 bg-red-900/20 border border-red-700/30 px-2 py-0.5 rounded-full animate-pulse">
                🔴 {criticalCount} crítico{criticalCount > 1 ? 's' : ''}
              </span>
            )}
            {warningCount > 0 && (
              <span className="flex items-center gap-1.5 text-xs text-yellow-400 bg-yellow-900/20 border border-yellow-700/30 px-2 py-0.5 rounded-full">
                ⚠ {warningCount} alerta{warningCount > 1 ? 's' : ''}
              </span>
            )}
            {criticalCount === 0 && warningCount === 0 && equipment.length > 0 && (
              <span className="flex items-center gap-1.5 text-xs text-emerald-400">
                ✅ Planta operativa
              </span>
            )}
          </div>

          <div className="ml-auto flex items-center gap-3">
            {/* Selector de industria */}
            {plantData?.industry && (
              <button
                onClick={() => setShowIndustrySelector(true)}
                className="hidden sm:flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg border border-slate-700/50 bg-slate-800/60 text-slate-300 hover:border-slate-600 hover:text-white transition-colors"
                title="Cambiar industria"
              >
                <span>{plantData.industry.icon}</span>
                <span className="max-w-[120px] truncate">{plantData.industry.site_name}</span>
              </button>
            )}
            {plantData && (
              <span className="hidden md:block text-xs text-slate-600 font-mono">
                tick #{plantData.tick}
              </span>
            )}
            <div className={`flex items-center gap-1.5 text-xs font-medium ${connected ? 'text-emerald-400' : 'text-red-400'}`}>
              {connected
                ? <><Wifi size={13} /> <span className="hidden sm:inline">Live</span></>
                : <><WifiOff size={13} /> <span>Offline</span></>
              }
            </div>
          </div>
        </div>

        {/* Navigation tabs */}
        <div className="max-w-screen-2xl mx-auto px-4 flex items-center gap-0.5 pb-0">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`relative flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors border-b-2 ${
                activeTab === tab.id
                  ? 'text-brand-500 border-brand-500'
                  : 'text-slate-500 border-transparent hover:text-slate-300'
              }`}
            >
              {tab.icon}
              {tab.label}
              {tab.id === 'alerts' && unackedAlerts > 0 && (
                <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-red-500 text-white text-[9px] flex items-center justify-center font-bold">
                  {unackedAlerts > 9 ? '9+' : unackedAlerts}
                </span>
              )}
            </button>
          ))}
        </div>
      </header>

      {/* Contenido principal */}
      <main className="flex-1 max-w-screen-2xl mx-auto w-full px-4 py-5">

        {/* ── TAB: OVERVIEW ─────────────────────────────────────────────────────── */}
        {activeTab === 'overview' && (
          <div className="space-y-5">
            <KPIBar plantData={plantData} />

            <div className="grid grid-cols-1 xl:grid-cols-[1fr_300px] gap-5">
              {/* Equipos */}
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <span className="w-1 h-3 bg-brand-500 rounded-full" />
                  <h2 className="text-xs uppercase text-slate-500 font-semibold">
                    Estado de Equipos
                  </h2>
                  {plantData && (
                    <span className="ml-auto text-xs text-slate-600 font-mono">
                      salud: {plantData.plant_health}%
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {equipment.map(eq => (
                    <EquipmentCard
                      key={eq.id}
                      eq={eq}
                      history={history[eq.id]}
                      onMaintenance={handleMaintenance}
                      onInjectFault={handleInjectFault}
                    />
                  ))}
                  {equipment.length === 0 && (
                    <div className="col-span-3 text-center text-slate-600 py-20 text-sm">
                      <div className="text-4xl mb-3">🏭</div>
                      Conectando con el simulador...
                    </div>
                  )}
                </div>
              </div>

              {/* Panel derecho */}
              <div className="space-y-4">
                <DemoControls onToast={showToast} />
                <AlertsPanel />
              </div>
            </div>
          </div>
        )}

        {/* ── TAB: WORK ORDERS ──────────────────────────────────────────────────── */}
        {activeTab === 'workorders' && (
          <div className="h-[calc(100vh-180px)]">
            <WorkOrderPanel />
          </div>
        )}

        {/* ── TAB: ALERTS ───────────────────────────────────────────────────────── */}
        {activeTab === 'alerts' && (
          <div className="max-w-2xl">
            <AlertsPanel />
          </div>
        )}

        {/* ── TAB: HISTORY ──────────────────────────────────────────────────────── */}
        {activeTab === 'history' && (
          <div className="max-w-2xl">
            <MaintenanceHistory />
          </div>
        )}

        {/* ── TAB: AGENT ────────────────────────────────────────────────────────── */}
        {activeTab === 'agent' && (
          <div className="h-[calc(100vh-180px)]">
            <AgentLog />
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/50 py-2 px-4 text-center text-[10px] text-slate-700 shrink-0">
        Industrial AI Demo · {plantData?.industry?.name ?? 'Sistema de Mantenimiento Predictivo'} · Powered by AI
      </footer>
    </div>

    {/* Industry selector modal */}
    {showIndustrySelector && (
      <IndustrySelector
        currentIndustryId={plantData?.industry?.id}
        onSelect={data => {
          showToast(`🏭 Cambiado a ${data.site}`)
          setShowIndustrySelector(false)
        }}
        onClose={() => setShowIndustrySelector(false)}
      />
    )}
  )
}

export default function App() {
  return (
    <PinGuardProvider>
      <AppInner />
    </PinGuardProvider>
  )
}
