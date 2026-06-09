import { useEffect, useState } from 'react'
import { Bell, BellOff, CheckCheck } from 'lucide-react'
import { usePinGuard } from '../context/PinGuard'

function timeAgo(ts) {
  const s = Math.floor(Date.now() / 1000 - ts)
  if (s < 60) return `${s}s`
  if (s < 3600) return `${Math.floor(s/60)}m`
  return `${Math.floor(s/3600)}h`
}

export function AlertsPanel() {
  const { protectedFetch } = usePinGuard()
  const [alerts, setAlerts] = useState([])
  const [showAll, setShowAll] = useState(false)

  useEffect(() => {
    fetchAlerts()
    const id = setInterval(fetchAlerts, 5000)
    return () => clearInterval(id)
  }, [showAll])

  async function fetchAlerts() {
    const url = showAll ? '/api/alerts?limit=40' : '/api/alerts?unacknowledged_only=true&limit=20'
    const res = await fetch(url)
    if (res.ok) setAlerts(await res.json())
  }

  async function ackAlert(id) {
    const res = await protectedFetch(`/api/alerts/${id}/acknowledge`, { method: 'POST' })
    if (res?.ok) fetchAlerts()
  }

  async function ackAll() {
    // Ack all en secuencia para reusar el PIN cacheado sin N modales
    const unacked = alerts.filter(a => !a.acknowledged)
    for (const a of unacked) {
      const res = await protectedFetch(`/api/alerts/${a.id}/acknowledge`, { method: 'POST' })
      if (!res) break  // usuario canceló
    }
    fetchAlerts()
  }

  const unackedCount = alerts.filter(a => !a.acknowledged).length

  return (
    <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 flex flex-col" style={{ maxHeight: 320 }}>
      <div className="p-3 border-b border-slate-700/50 flex items-center gap-2 shrink-0">
        <Bell size={14} className="text-yellow-400" />
        <h3 className="text-sm font-semibold text-white">Alertas</h3>
        {unackedCount > 0 && (
          <span className="px-1.5 py-0.5 rounded-full bg-red-500/20 text-red-400 text-[10px] font-bold border border-red-500/30">
            {unackedCount}
          </span>
        )}
        <div className="ml-auto flex items-center gap-2">
          {unackedCount > 0 && (
            <button onClick={ackAll} className="text-[10px] text-slate-500 hover:text-slate-300 flex items-center gap-1">
              <CheckCheck size={11} /> Ack all
            </button>
          )}
          <button
            onClick={() => setShowAll(!showAll)}
            className={`text-[10px] px-2 py-0.5 rounded border transition-colors ${
              showAll
                ? 'text-brand-500 border-brand-500/30 bg-brand-500/10'
                : 'text-slate-500 border-slate-600/30'
            }`}
          >
            {showAll ? 'Solo activas' : 'Ver todas'}
          </button>
        </div>
      </div>

      <div className="overflow-y-auto flex-1 p-2 space-y-1">
        {alerts.length === 0 && (
          <div className="text-center text-slate-600 text-xs py-6 flex flex-col items-center gap-2">
            <BellOff size={20} className="text-slate-700" />
            Sin alertas activas
          </div>
        )}
        {alerts.map(alert => (
          <div
            key={alert.id}
            className={`flex items-center gap-2 px-2 py-1.5 rounded text-xs transition-opacity ${
              alert.acknowledged ? 'opacity-40' : ''
            } ${
              alert.severity === 'critical'
                ? 'bg-red-900/20 border border-red-700/30'
                : 'bg-yellow-900/20 border border-yellow-700/30'
            }`}
          >
            <span className={`shrink-0 ${alert.severity === 'critical' ? 'text-red-400' : 'text-yellow-400'}`}>
              {alert.severity === 'critical' ? '🔴' : '🟡'}
            </span>
            <div className="flex-1 min-w-0">
              <div className="truncate text-white">{alert.equipment_name}</div>
              <div className="text-slate-400 truncate">{alert.message}</div>
            </div>
            <span className="text-slate-600 shrink-0">{timeAgo(alert.created_at)}</span>
            {!alert.acknowledged && (
              <button
                onClick={() => ackAlert(alert.id)}
                className="shrink-0 p-0.5 hover:text-emerald-400 text-slate-600 transition-colors"
                title="Acknowledge"
              >
                <CheckCheck size={12} />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
