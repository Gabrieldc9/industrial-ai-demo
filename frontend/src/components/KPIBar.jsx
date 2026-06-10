import { useEffect, useState } from 'react'
import { Activity, AlertTriangle, ClipboardList, Users, Gauge } from 'lucide-react'

const STATUS_COLOR = {
  ok:       { text: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20' },
  warning:  { text: 'text-yellow-400',  bg: 'bg-yellow-500/10',  border: 'border-yellow-500/30' },
  critical: { text: 'text-red-400',     bg: 'bg-red-500/10',     border: 'border-red-500/40 animate-pulse' },
}

function IndustryKPI({ kpi }) {
  const col = STATUS_COLOR[kpi.status] || STATUS_COLOR.ok
  return (
    <div className={`bg-slate-800/60 rounded-xl border ${col.border} p-4 transition-all duration-500`}>
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs uppercase text-slate-500 tracking-wide font-medium">{kpi.label}</div>
        <div className={`w-2 h-2 rounded-full ${
          kpi.status === 'ok' ? 'bg-emerald-400' :
          kpi.status === 'warning' ? 'bg-yellow-400 animate-pulse' :
          'bg-red-400 animate-ping'
        }`} />
      </div>
      <div className={`text-2xl font-bold tracking-tight ${col.text}`}>
        {kpi.value}
        {kpi.unit && <span className="text-sm font-normal text-slate-500 ml-1">{kpi.unit}</span>}
      </div>
    </div>
  )
}

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

  const industryKpis = plantData?.industry_kpis
  const health    = plantData?.plant_health ?? stats?.plant_health ?? 0
  const healthCol = health > 70 ? STATUS_COLOR.ok : health > 40 ? STATUS_COLOR.warning : STATUS_COLOR.critical
  const faults    = plantData?.active_faults?.length ?? 0
  const critical  = stats?.equipment_status?.critical ?? 0

  // Si hay KPIs específicos de industria, mostrarlos en lugar del genérico
  if (industryKpis?.length) {
    return (
      <div className="space-y-2">
        {/* Fila 1: KPIs de industria */}
        <div className={`grid gap-3`} style={{ gridTemplateColumns: `repeat(${industryKpis.length}, minmax(0, 1fr))` }}>
          {industryKpis.map(kpi => <IndustryKPI key={kpi.label} kpi={kpi} />)}
        </div>

        {/* Fila 2: KPIs universales (salud, fallas, WOs, viewers) */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Salud planta */}
          <div className={`bg-slate-800/40 rounded-xl border ${healthCol.border} p-3 flex items-center gap-3`}>
            <Activity size={14} className={healthCol.text} />
            <div>
              <div className="text-[10px] uppercase text-slate-600">Salud planta</div>
              <div className={`text-lg font-bold ${healthCol.text}`}>{health.toFixed(0)}%</div>
            </div>
            <div className="ml-auto h-1 w-16 bg-slate-700 rounded-full overflow-hidden">
              <div className={`h-full rounded-full ${health > 70 ? 'bg-emerald-500' : health > 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
                   style={{ width: `${Math.max(2, health)}%` }} />
            </div>
          </div>

          {/* Fallas */}
          <div className={`bg-slate-800/40 rounded-xl border p-3 flex items-center gap-3 ${faults > 0 ? 'border-red-500/30' : 'border-slate-700/30'}`}>
            <AlertTriangle size={14} className={faults > 0 ? 'text-red-400' : 'text-slate-500'} />
            <div>
              <div className="text-[10px] uppercase text-slate-600">Fallas activas</div>
              <div className={`text-lg font-bold ${faults > 0 ? 'text-red-400' : 'text-emerald-400'}`}>{faults}</div>
            </div>
            {critical > 0 && (
              <span className="ml-auto text-[10px] text-red-400 bg-red-900/20 border border-red-700/30 px-1.5 py-0.5 rounded animate-pulse">
                {critical} crítico{critical > 1 ? 's' : ''}
              </span>
            )}
          </div>

          {/* Work Orders */}
          <div className="bg-slate-800/40 rounded-xl border border-slate-700/30 p-3 flex items-center gap-3">
            <ClipboardList size={14} className="text-blue-400" />
            <div>
              <div className="text-[10px] uppercase text-slate-600">Work Orders</div>
              <div className="text-lg font-bold text-blue-400">{stats?.wo_summary?.open ?? 0}</div>
            </div>
            <div className="ml-auto text-right text-[10px] text-slate-600">
              <div>{stats?.wo_summary?.completed ?? 0} completadas</div>
              <div>{stats?.wo_summary?.in_progress ?? 0} en curso</div>
            </div>
          </div>

          {/* Viewers */}
          <div className="bg-slate-800/40 rounded-xl border border-slate-700/30 p-3 flex items-center gap-3">
            <Users size={14} className="text-purple-400" />
            <div>
              <div className="text-[10px] uppercase text-slate-600">Viewers live</div>
              <div className="text-lg font-bold text-purple-400">{stats?.connected_clients ?? 0}</div>
            </div>
            <div className="ml-auto text-right text-[10px] text-slate-600 flex items-center gap-1">
              <Gauge size={10} /> #{plantData?.tick ?? '—'}
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Fallback: KPIBar genérico original (manufactura sin industry_kpis)
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div className={`bg-slate-800/60 rounded-xl border ${healthCol.border} p-4`}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-1.5 text-slate-400 text-xs uppercase tracking-wide">
            <Activity size={13} /> Salud Planta
          </div>
        </div>
        <div className={`text-3xl font-bold tracking-tight ${healthCol.text}`}>
          {health.toFixed(0)}<span className="text-lg">%</span>
        </div>
        <div className="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div className={`h-full rounded-full transition-all duration-700 ${health > 70 ? 'bg-emerald-500' : health > 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
               style={{ width: `${Math.max(2, health)}%` }} />
        </div>
      </div>
      <div className={`bg-slate-800/60 rounded-xl border p-4 ${faults > 0 ? 'border-red-500/30' : 'border-slate-700/50'}`}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-1.5 text-slate-400 text-xs uppercase tracking-wide">
            <AlertTriangle size={13} /> Fallas
          </div>
        </div>
        <div className={`text-3xl font-bold ${faults > 0 ? 'text-red-400' : 'text-emerald-400'}`}>{faults}</div>
        <div className="text-xs text-slate-500 mt-2">{critical > 0 ? <span className="text-red-400">{critical} crítico{critical > 1 ? 's' : ''}</span> : 'Todos operativos'}</div>
      </div>
      <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 p-4">
        <div className="flex items-center gap-1.5 text-slate-400 text-xs uppercase tracking-wide mb-3">
          <ClipboardList size={13} /> Work Orders
        </div>
        <div className="text-3xl font-bold text-blue-400">{stats?.wo_summary?.open ?? 0}</div>
        <div className="text-xs text-slate-600 mt-2">{stats?.wo_summary?.completed ?? 0} completadas</div>
      </div>
      <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 p-4">
        <div className="flex items-center gap-1.5 text-slate-400 text-xs uppercase tracking-wide mb-3">
          <Users size={13} /> Viewers Live
        </div>
        <div className="text-3xl font-bold text-purple-400">{stats?.connected_clients ?? 0}</div>
        <div className="text-xs text-slate-500 mt-2 flex items-center gap-1"><Gauge size={11} /> Tick #{plantData?.tick ?? '—'}</div>
      </div>
    </div>
  )
}
