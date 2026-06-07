import { useEffect, useState } from 'react'
import { Activity, AlertTriangle, ClipboardList, Users } from 'lucide-react'

export function KPIBar({ plantData }) {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    fetchStats()
    const id = setInterval(fetchStats, 5000)
    return () => clearInterval(id)
  }, [])

  async function fetchStats() {
    const res = await fetch('/api/stats')
    if (res.ok) setStats(await res.json())
  }

  const health = plantData?.plant_health ?? stats?.plant_health ?? 0
  const healthColor = health > 70 ? 'text-emerald-400' : health > 40 ? 'text-yellow-400' : 'text-red-400'

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {/* Plant Health */}
      <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 p-4">
        <div className="flex items-center gap-2 text-slate-400 text-xs mb-2">
          <Activity size={14} /> SALUD PLANTA
        </div>
        <div className={`text-3xl font-bold ${healthColor}`}>
          {health.toFixed(0)}%
        </div>
        <div className="h-1 mt-2 bg-slate-700 rounded-full">
          <div
            className={`h-full rounded-full transition-all duration-700 ${
              health > 70 ? 'bg-emerald-500' : health > 40 ? 'bg-yellow-500' : 'bg-red-500'
            }`}
            style={{ width: `${health}%` }}
          />
        </div>
      </div>

      {/* Fallas activas */}
      <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 p-4">
        <div className="flex items-center gap-2 text-slate-400 text-xs mb-2">
          <AlertTriangle size={14} /> FALLAS ACTIVAS
        </div>
        <div className={`text-3xl font-bold ${
          (stats?.active_faults ?? 0) > 0 ? 'text-red-400' : 'text-emerald-400'
        }`}>
          {stats?.active_faults ?? plantData?.active_faults?.length ?? 0}
        </div>
        <div className="text-xs text-slate-500 mt-2">
          {stats?.equipment_status?.critical ?? 0} equipos críticos
        </div>
      </div>

      {/* WOs abiertas */}
      <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 p-4">
        <div className="flex items-center gap-2 text-slate-400 text-xs mb-2">
          <ClipboardList size={14} /> WOs ABIERTAS
        </div>
        <div className="text-3xl font-bold text-blue-400">
          {stats?.wo_summary?.open ?? 0}
        </div>
        <div className="text-xs text-slate-500 mt-2">
          {stats?.wo_summary?.completed ?? 0} completadas hoy
        </div>
      </div>

      {/* Clientes conectados */}
      <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 p-4">
        <div className="flex items-center gap-2 text-slate-400 text-xs mb-2">
          <Users size={14} /> VIEWERS LIVE
        </div>
        <div className="text-3xl font-bold text-purple-400">
          {stats?.connected_clients ?? 0}
        </div>
        <div className="flex items-center gap-1 text-xs text-slate-500 mt-2">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Streaming activo
        </div>
      </div>
    </div>
  )
}
