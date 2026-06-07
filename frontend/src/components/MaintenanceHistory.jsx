import { useEffect, useState } from 'react'
import { Wrench } from 'lucide-react'

function timeAgo(ts) {
  const s = Math.floor(Date.now() / 1000 - ts)
  if (s < 60) return `${s}s`
  if (s < 3600) return `${Math.floor(s/60)}m`
  if (s < 86400) return `${Math.floor(s/3600)}h`
  return `${Math.floor(s/86400)}d`
}

export function MaintenanceHistory() {
  const [logs, setLogs] = useState([])

  useEffect(() => {
    fetchLogs()
    const id = setInterval(fetchLogs, 8000)
    return () => clearInterval(id)
  }, [])

  async function fetchLogs() {
    const res = await fetch('/api/maintenance-log?limit=15')
    if (res.ok) setLogs(await res.json())
  }

  return (
    <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 flex flex-col" style={{ maxHeight: 280 }}>
      <div className="p-3 border-b border-slate-700/50 flex items-center gap-2 shrink-0">
        <Wrench size={14} className="text-blue-400" />
        <h3 className="text-sm font-semibold text-white">Historial de Mantenimiento</h3>
        <span className="ml-auto text-[10px] text-slate-500">{logs.length} registros</span>
      </div>

      <div className="overflow-y-auto flex-1 p-2 space-y-1">
        {logs.length === 0 && (
          <div className="text-center text-slate-600 text-xs py-6">Sin intervenciones aún</div>
        )}
        {logs.map(log => {
          const healthDelta = log.health_after - log.health_before
          return (
            <div key={log.id} className="flex items-center gap-2 px-2 py-1.5 rounded bg-slate-700/30 border border-slate-600/20 text-xs">
              <Wrench size={11} className="text-blue-400 shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-white truncate">{log.equipment_id}</div>
                <div className="text-slate-500 text-[10px]">
                  {log.action.replace(/_/g, ' ')}
                  {log.notes ? ` · ${log.notes}` : ''}
                </div>
              </div>
              <div className="text-right shrink-0">
                <div className={`font-mono font-bold ${healthDelta >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {healthDelta > 0 ? '+' : ''}{healthDelta.toFixed(1)}%
                </div>
                <div className="text-[10px] text-slate-600">{timeAgo(log.performed_at)}</div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
