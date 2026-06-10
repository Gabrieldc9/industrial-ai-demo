import { useEffect, useState } from 'react'
import { BrainCircuit, Shield, Wrench, Settings, Zap } from 'lucide-react'
import { usePinGuard } from '../context/PinGuard'

// ─── Iconos por agente ────────────────────────────────────────────────────────

const AGENT_ICONS = {
  safety:      <Shield size={16} className="text-red-400" />,
  maintenance: <Wrench size={16} className="text-blue-400" />,
  process:     <Settings size={16} className="text-emerald-400" />,
}

const AGENT_COLORS = {
  safety:      { border: 'border-red-500/30',     bg: 'bg-red-500/5',     dot: 'bg-red-400',     text: 'text-red-400'     },
  maintenance: { border: 'border-blue-500/30',    bg: 'bg-blue-500/5',    dot: 'bg-blue-400',    text: 'text-blue-400'    },
  process:     { border: 'border-emerald-500/30', bg: 'bg-emerald-500/5', dot: 'bg-emerald-400', text: 'text-emerald-400' },
}

// ─── Modos de autonomía ───────────────────────────────────────────────────────

const MODES = [
  {
    id: 'manual',
    label: 'Manual',
    desc: 'Solo observa',
    color: 'text-slate-400 border-slate-600/40 bg-slate-700/20 hover:bg-slate-700/40',
    active: 'text-slate-300 border-slate-500/60 bg-slate-700/50',
  },
  {
    id: 'assisted',
    label: 'Asistido',
    desc: 'WOs automáticas',
    color: 'text-blue-400 border-blue-600/30 bg-blue-900/10 hover:bg-blue-900/20',
    active: 'text-blue-300 border-blue-500/50 bg-blue-900/25',
  },
  {
    id: 'autonomous',
    label: 'Autónomo',
    desc: 'Actúa solo',
    color: 'text-emerald-400 border-emerald-600/30 bg-emerald-900/10 hover:bg-emerald-900/20',
    active: 'text-emerald-300 border-emerald-500/50 bg-emerald-900/25',
  },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function timeAgo(ts) {
  if (!ts) return '—'
  const s = Math.floor(Date.now() / 1000 - ts)
  if (s < 5)  return 'ahora'
  if (s < 60) return `${s}s`
  if (s < 3600) return `${Math.floor(s/60)}m`
  return `${Math.floor(s/3600)}h`
}

const LOG_ICON = {
  alert_detected:        '🔔',
  wo_created:            '📋',
  diagnosis:             '🤖',
  maintenance_triggered: '🔧',
  rule_fired:            '⚡',
}

const LOG_COLOR = {
  alert_detected:        'text-yellow-400',
  wo_created:            'text-blue-400',
  diagnosis:             'text-purple-400',
  maintenance_triggered: 'text-emerald-400',
  rule_fired:            'text-slate-400',
}

// ─── Componente AgentCard ─────────────────────────────────────────────────────

function AgentCard({ agent }) {
  const col = AGENT_COLORS[agent.id] || AGENT_COLORS.maintenance

  return (
    <div className={`rounded-xl border ${col.border} ${col.bg} p-4 flex flex-col gap-3`}>
      {/* Header */}
      <div className="flex items-center gap-2.5">
        <div className={`w-8 h-8 rounded-lg border ${col.border} bg-slate-900/60 flex items-center justify-center shrink-0`}>
          {AGENT_ICONS[agent.id] || <BrainCircuit size={15} className="text-slate-400" />}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-white truncate">{agent.name}</span>
            <span className={`w-1.5 h-1.5 rounded-full ${col.dot} animate-pulse shrink-0`} />
          </div>
          <div className="text-[10px] text-slate-500 truncate">{agent.domain}</div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-1.5">
        {Object.entries(agent.stats || {}).map(([k, v]) => (
          <div key={k} className="rounded-lg bg-slate-800/60 px-2 py-1.5">
            <div className={`text-lg font-bold leading-none ${col.text}`}>{v}</div>
            <div className="text-[9px] text-slate-600 uppercase mt-0.5 leading-tight">
              {k.replace(/_/g, ' ')}
            </div>
          </div>
        ))}
      </div>

      {/* Última acción */}
      <div className="text-[11px] leading-snug text-slate-400 min-h-[2.5rem]">
        <span className="text-slate-600 mr-1">{timeAgo(agent.last_action_ts)}</span>
        {agent.last_action}
      </div>
    </div>
  )
}

// ─── Componente principal ─────────────────────────────────────────────────────

export function AgentOrchestra() {
  const { protectedFetch } = usePinGuard()
  const [status, setStatus]       = useState(null)
  const [logs, setLogs]           = useState([])
  const [settingMode, setMode]    = useState(null)

  useEffect(() => {
    fetchAll()
    const id = setInterval(fetchAll, 3000)
    return () => clearInterval(id)
  }, [])

  async function fetchAll() {
    const [s, l] = await Promise.all([
      fetch('/api/agents/status').then(r => r.ok ? r.json() : null),
      fetch('/api/agent-log?limit=40').then(r => r.ok ? r.json() : []),
    ])
    if (s) setStatus(s)
    setLogs(l)
  }

  async function handleSetMode(mode) {
    setMode(mode)
    await protectedFetch('/api/agents/mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode }),
    })
    await fetchAll()
    setMode(null)
  }

  const currentMode = status?.autonomy_mode || 'assisted'
  const agents      = status?.agents || []

  return (
    <div className="space-y-5 h-full flex flex-col">

      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center">
            <BrainCircuit size={18} className="text-brand-500" />
          </div>
          <div>
            <h2 className="text-white font-bold text-sm leading-none">Cerebro de la Planta</h2>
            <p className="text-[11px] text-slate-500 mt-0.5">
              {agents.length} agentes activos · {status?.autonomy_description ?? '—'}
            </p>
          </div>
        </div>

        {/* Toggle de autonomía */}
        <div className="sm:ml-auto flex items-center gap-1.5 bg-slate-800/60 border border-slate-700/40 rounded-xl p-1">
          {MODES.map(m => {
            const isActive = currentMode === m.id
            return (
              <button
                key={m.id}
                onClick={() => handleSetMode(m.id)}
                disabled={settingMode !== null || isActive}
                className={`flex flex-col items-center gap-0.5 px-3 py-2 rounded-lg border text-xs font-medium transition-all ${
                  isActive ? m.active : m.color
                } ${settingMode === m.id ? 'opacity-50' : ''}`}
              >
                <span>{m.label}</span>
                <span className={`text-[9px] font-normal ${isActive ? 'opacity-80' : 'opacity-50'}`}>
                  {m.desc}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* ── Grid de agentes ───────────────────────────────────────────────── */}
      {currentMode === 'autonomous' && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-900/20 border border-emerald-600/30 text-xs text-emerald-300">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping shrink-0" />
          Modo autónomo activo — los agentes pueden ejecutar acciones sin aprobación humana
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {agents.map(agent => (
          <AgentCard key={agent.id} agent={agent} />
        ))}
        {agents.length === 0 && (
          <div className="col-span-3 text-center text-slate-600 py-16 text-sm">
            <div className="text-4xl mb-3">🤖</div>
            Conectando con los agentes...
          </div>
        )}
      </div>

      {/* ── Timeline de decisiones ────────────────────────────────────────── */}
      <div className="flex-1 min-h-0 bg-slate-800/40 rounded-xl border border-slate-700/40 flex flex-col overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700/40 flex items-center gap-2 shrink-0">
          <Zap size={13} className="text-slate-500" />
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
            Timeline de decisiones
          </span>
          <span className="ml-auto w-1.5 h-1.5 rounded-full bg-brand-500 animate-pulse" />
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-1 font-mono">
          {logs.map(log => {
            const icon  = LOG_ICON[log.action_type]  || '⚡'
            const color = LOG_COLOR[log.action_type] || 'text-slate-400'

            // Color del agente según prefijo del summary
            const isSafety  = log.summary?.startsWith('🛡️') || log.summary?.includes('[SAFETY')
            const isMaint   = log.action_type !== 'rule_fired' && !isSafety
            const isProcess = log.summary?.startsWith('⚙️') || log.summary?.startsWith('🤖 [AUTÓNOMO]')

            const rowColor = isSafety  ? 'border-l-2 border-red-500/40 pl-2'
                           : isProcess ? 'border-l-2 border-emerald-500/40 pl-2'
                           : isMaint   ? 'border-l-2 border-blue-500/40 pl-2'
                           : 'pl-2 opacity-60'

            return (
              <div
                key={log.id}
                className={`flex gap-2 text-xs py-0.5 group ${rowColor}`}
              >
                <span className="text-slate-600 shrink-0 w-8 text-right tabular-nums">
                  {timeAgo(log.timestamp)}
                </span>
                <span className="shrink-0">{icon}</span>
                <span className={`${color} leading-snug break-words min-w-0`}>
                  {log.summary}
                </span>
              </div>
            )
          })}
          {logs.length === 0 && (
            <div className="text-slate-600 text-xs text-center py-8">
              Esperando actividad de los agentes...
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
