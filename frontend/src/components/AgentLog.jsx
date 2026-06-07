import { useEffect, useState } from 'react'
import { Bot } from 'lucide-react'

const ACTION_CFG = {
  alert_detected:        { icon: '🔔', color: 'text-yellow-400' },
  wo_created:            { icon: '📋', color: 'text-blue-400' },
  diagnosis:             { icon: '🤖', color: 'text-purple-400' },
  maintenance_triggered: { icon: '🔧', color: 'text-emerald-400' },
  rule_fired:            { icon: '⚡', color: 'text-slate-400' },
}

function timeAgo(ts) {
  const s = Math.floor(Date.now() / 1000 - ts)
  if (s < 60) return `${s}s`
  if (s < 3600) return `${Math.floor(s/60)}m`
  return `${Math.floor(s/3600)}h`
}

export function AgentLog() {
  const [logs, setLogs] = useState([])

  useEffect(() => {
    fetchLogs()
    const id = setInterval(fetchLogs, 3000)
    return () => clearInterval(id)
  }, [])

  async function fetchLogs() {
    const res = await fetch('/api/agent-log?limit=30')
    if (res.ok) setLogs(await res.json())
  }

  return (
    <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 flex flex-col h-full">
      <div className="p-4 border-b border-slate-700/50 flex items-center gap-2">
        <Bot size={16} className="text-purple-400" />
        <h2 className="font-semibold text-white">Agente IA — Actividad</h2>
        <span className="ml-auto w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-1.5 font-mono">
        {logs.map(log => {
          const cfg = ACTION_CFG[log.action_type] || ACTION_CFG.rule_fired
          return (
            <div key={log.id} className="flex gap-2 text-xs group">
              <span className="text-slate-600 shrink-0 w-8">{timeAgo(log.timestamp)}</span>
              <span className="shrink-0">{cfg.icon}</span>
              <span className={`${cfg.color} leading-snug`}>{log.summary}</span>
            </div>
          )
        })}
        {logs.length === 0 && (
          <div className="text-slate-600 text-xs text-center py-4">Esperando actividad...</div>
        )}
      </div>
    </div>
  )
}
