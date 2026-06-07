import { useEffect, useState } from 'react'
import { Activity, AlertTriangle, ClipboardList, Users, Gauge } from 'lucide-react'

export function KPIBar({ plantData }) {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    fetchStats()
    const id = setInterval(fetchStats, 4000)
    return () => clearInterval(id)
  }, [])

  async function fetchStats() {
    const res = await fetch('/api/stats')
    if (res.ok) setStats(await res.json())
  }

  const health = plantData?.plant_health ?? stats?.plant_health ?? 0
  const healthColor = health > 70 ? 'text-emerald-400' : health > 40 ? 'text-yellow-400' : 'text-red-400'
  const healthBorder = health > 70 ? 'border-emerald-500/20' : health > 40 ? 'border-yellow-500/30' : 'border-red-500/40'

  const faults = stats?.active_faults ?? plantData?.active_faults?.length ?? 0
  const critical = stats?.equipment_status?.critical ?? 0

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">

      {/* Salud de la planta */}
      <div className={`bg-slate-800/60 rounded-xl border ${healthBorder} p-4 transition-colors duration-500`}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-1.5 text-slate-400 text-xs uppercase tracking-wide">
            <Activity size={13} /> Salud Planta
          </div>
          <div className={`text-xs font-bold px-1.5 py-0.5 rounded ${
            health > 70 ? 'bg-emerald-500/10 text-emerald-400' :
            health > 40 ? 'bg-yellow-500/10 text-yellow-400' :
            'bg-red-500/10 text-red-400 animate-pulse'
          }`}>
            {health > 70 ? '●' : health > 40 ? '▲' : '✕'}
          </div>
        </div>
        <div className={`text-3xl font-bold tracking-tight ${healthColor}`}>
          {health.toFixed(0)}<span className="text-lg">%</span>
        </div>
        <div className="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${
              health > 70 ? 'bg-emerald-500' : health > 40 ? 'bg-yellow-500' : 'bg-red-500'
            }`}
            style={{ width: `${Math.max(2, health)}%` }}
          />
        </div>
      </div>

      {/* Fallas activas */}
      <div className={`bg-slate-800/60 rounded-xl border p-4 transition-colors duration-500 ${
        faults > 0 ? 'border-red-500/30' : 'border-slate-700/50'
      }`}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-1.5 text-slate-400 text-xs uppercase tracking-wide">
            <AlertTriangle size={13} /> Fallas
          </div>
          {faults > 0 && (
            <span className="text-[10px] text-red-400 bg-red-900/20 border border-red-700/30 px-1.5 py-0.5 rounded animate-pulse">
              ACTIVO
            </span>
          )}
        </div>
        <div className={`text-3xl font-bold tracking-tight ${faults > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
          {faults}
        </div>
        <div className="text-xs text-slate-500 mt-2">
          {critical > 0 ? (
            <span className="text-red-400">{critical} en estado crítico</span>
          ) : (
            'Todos operativos'
          )}
        </div>
      </div>

      {/* Work Orders */}
      <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-1.5 text-slate-400 text-xs uppercase tracking-wide">
            <ClipboardList size={13} /> Work Orders
          </div>
          {(stats?.wo_summary?.open ?? 0) > 0 && (
            <span className="text-[10px] text-blue-400 bg-blue-900/20 border border-blue-700/30 px-1.5 py-0.5 rounded">
              {stats.wo_summary.open} abiertas
            </span>
          )}
        </div>
        <div className="flex items-end gap-3">
          <div className="text-3xl font-bold tracking-tight text-blue-400">
            {stats?.wo_summary?.open ?? 0}
          </div>
          <div className="text-xs text-slate-600 mb-1 space-y-0.5">
            <div>{stats?.wo_summary?.completed ?? 0} completadas</div>
            <div>{stats?.wo_summary?.in_progress ?? 0} en curso</div>
          </div>
        </div>
      </div>

      {/* Viewers live */}
      <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-1.5 text-slate-400 text-xs uppercase tracking-wide">
            <Users size={13} /> Viewers Live
          </div>
          <div className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[10px] text-emerald-400">LIVE</span>
          </div>
        </div>
        <div className="text-3xl font-bold tracking-tight text-purple-400">
          {stats?.connected_clients ?? 0}
        </div>
        <div className="text-xs text-slate-500 mt-2 flex items-center gap-1.5">
          <Gauge size={11} />
          Tick #{plantData?.tick ?? '—'}
        </div>
      </div>

    </div>
  )
}
