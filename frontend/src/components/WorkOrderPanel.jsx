import { useEffect, useState } from 'react'
import { ClipboardList, CheckCircle, AlertTriangle, Clock } from 'lucide-react'

const PRIORITY_CFG = {
  critical: 'text-red-400 bg-red-900/20 border-red-700/30',
  high:     'text-orange-400 bg-orange-900/20 border-orange-700/30',
  medium:   'text-yellow-400 bg-yellow-900/20 border-yellow-700/30',
  low:      'text-slate-400 bg-slate-700/20 border-slate-600/30',
}

const STATUS_CFG = {
  open:        { label: 'Abierta',       icon: <Clock size={12} />,         cls: 'text-yellow-400' },
  in_progress: { label: 'En progreso',   icon: <AlertTriangle size={12} />, cls: 'text-blue-400' },
  completed:   { label: 'Completada',    icon: <CheckCircle size={12} />,   cls: 'text-emerald-400' },
  cancelled:   { label: 'Cancelada',     icon: null,                        cls: 'text-slate-500' },
}

function timeAgo(ts) {
  const s = Math.floor(Date.now() / 1000 - ts)
  if (s < 60) return `${s}s`
  if (s < 3600) return `${Math.floor(s/60)}m`
  return `${Math.floor(s/3600)}h`
}

export function WorkOrderPanel() {
  const [wos, setWos] = useState([])
  const [selected, setSelected] = useState(null)
  const [tab, setTab] = useState('open')

  useEffect(() => {
    fetchWos()
    const id = setInterval(fetchWos, 5000)
    return () => clearInterval(id)
  }, [tab])

  async function fetchWos() {
    const res = await fetch(`/api/work-orders?status=${tab}&limit=20`)
    if (res.ok) setWos(await res.json())
  }

  async function updateStatus(woId, status) {
    await fetch(`/api/work-orders/${woId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    })
    fetchWos()
    if (selected?.id === woId) setSelected(null)
  }

  const tabs = [
    { key: 'open', label: 'Abiertas' },
    { key: 'in_progress', label: 'En curso' },
    { key: 'completed', label: 'Completadas' },
  ]

  return (
    <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-slate-700/50">
        <div className="flex items-center gap-2 mb-3">
          <ClipboardList size={16} className="text-brand-500" />
          <h2 className="font-semibold text-white">Órdenes de Trabajo</h2>
          <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-500 font-bold">
            {wos.length}
          </span>
        </div>
        <div className="flex gap-1">
          {tabs.map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex-1 text-xs py-1 rounded transition-colors ${
                tab === t.key
                  ? 'bg-brand-500/20 text-brand-500 border border-brand-500/30'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Lista */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {wos.length === 0 && (
          <div className="text-center text-slate-600 text-sm py-8">
            No hay WOs {tab === 'open' ? 'abiertas' : tab === 'completed' ? 'completadas' : 'en curso'}
          </div>
        )}
        {wos.map(wo => (
          <div
            key={wo.id}
            onClick={() => setSelected(selected?.id === wo.id ? null : wo)}
            className={`rounded-lg border p-3 cursor-pointer transition-all ${
              PRIORITY_CFG[wo.priority] || PRIORITY_CFG.medium
            } ${selected?.id === wo.id ? 'ring-1 ring-brand-500/50' : 'hover:brightness-110'}`}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="text-xs font-mono text-slate-400 mb-0.5">{wo.wo_number}</div>
                <div className="text-sm font-medium text-white leading-tight">{wo.title}</div>
                <div className="text-xs text-slate-400 mt-1">{wo.equipment_name}</div>
              </div>
              <div className="flex flex-col items-end gap-1 shrink-0">
                <span className={`text-[10px] font-bold uppercase ${STATUS_CFG[wo.status]?.cls}`}>
                  {STATUS_CFG[wo.status]?.label}
                </span>
                <span className="text-[10px] text-slate-600">{timeAgo(wo.created_at)}</span>
              </div>
            </div>

            {/* Detalle expandido */}
            {selected?.id === wo.id && (
              <div className="mt-3 pt-3 border-t border-white/10 space-y-2">
                {wo.ai_diagnosis && (
                  <div>
                    <div className="text-[10px] uppercase text-slate-500 mb-1">🤖 Diagnóstico IA</div>
                    <p className="text-xs text-slate-300">{wo.ai_diagnosis}</p>
                  </div>
                )}
                {wo.ai_recommendation && (
                  <div>
                    <div className="text-[10px] uppercase text-slate-500 mb-1">📋 Recomendación</div>
                    <p className="text-xs text-slate-400">{wo.ai_recommendation}</p>
                  </div>
                )}
                {wo.fault_mode && (
                  <div className="text-xs">
                    <span className="text-slate-500">Modo de falla: </span>
                    <span className="text-red-300">{wo.fault_mode}</span>
                  </div>
                )}
                {tab === 'open' && (
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={e => { e.stopPropagation(); updateStatus(wo.id, 'in_progress') }}
                      className="flex-1 text-xs py-1 rounded bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 border border-blue-500/30"
                    >
                      Iniciar
                    </button>
                    <button
                      onClick={e => { e.stopPropagation(); updateStatus(wo.id, 'completed') }}
                      className="flex-1 text-xs py-1 rounded bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-300 border border-emerald-500/30"
                    >
                      Completar
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
