import { useState } from 'react'
import { Play, Pause, RotateCcw, Zap, AlertTriangle, Heart, BrainCircuit } from 'lucide-react'
import { usePinGuard } from '../context/PinGuard'

const SPEEDS = [
  { label: '0.5×', value: 0.5 },
  { label: '1×',   value: 1   },
  { label: '2×',   value: 2   },
  { label: '5×',   value: 5   },
  { label: '10×',  value: 10  },
]

const SCENARIOS = [
  { id: 'planta_futuro', label: 'Planta del Futuro', icon: <BrainCircuit size={13} />, color: 'text-brand-500 bg-brand-500/10 border-brand-500/30 hover:bg-brand-500/20' },
  { id: 'cascade',       label: 'Falla Cascada',     icon: <Zap size={13} />,           color: 'text-orange-400 bg-orange-900/20 border-orange-700/40 hover:bg-orange-900/40' },
  { id: 'critical',      label: 'Crisis Total',      icon: <AlertTriangle size={13} />, color: 'text-red-400 bg-red-900/20 border-red-700/40 hover:bg-red-900/40' },
  { id: 'recovery',      label: 'Recuperación',      icon: <Heart size={13} />,         color: 'text-emerald-400 bg-emerald-900/20 border-emerald-700/40 hover:bg-emerald-900/40' },
]

export function DemoControls({ onToast }) {
  const { protectedFetch } = usePinGuard()
  const [speed, setSpeed] = useState(1)
  const [paused, setPaused] = useState(false)
  const [loading, setLoading] = useState(null)

  async function setSimSpeed(v) {
    setLoading('speed')
    const res = await protectedFetch('/api/plant/speed', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ multiplier: v }),
    })
    if (res?.ok) setSpeed(v)
    setLoading(null)
  }

  async function togglePause() {
    setLoading('pause')
    const res = await protectedFetch('/api/plant/pause', { method: 'POST' })
    if (res?.ok) {
      const data = await res.json()
      setPaused(data.paused)
    }
    setLoading(null)
  }

  async function resetPlant() {
    if (!confirm('¿Resetear toda la planta y limpiar la base de datos?')) return
    setLoading('reset')
    const res = await protectedFetch('/api/plant/reset', { method: 'POST' })
    if (res?.ok) {
      setSpeed(1)
      setPaused(false)
      onToast?.('🔄 Planta reseteada al estado inicial')
    }
    setLoading(null)
  }

  async function runScenario(id) {
    setLoading(id)
    const res = await protectedFetch(`/api/demo/scenario/${id}`, { method: 'POST' })
    if (res?.ok) {
      const data = await res.json()
      const msg = id === 'planta_futuro'
        ? `🏭 Planta del Futuro: 3 agentes respondiendo en ${data.affected?.join(', ')} — mirá el tab Cerebro`
        : id === 'cascade'
        ? `⚡ Cascada activa en ${data.affected?.join(', ')}`
        : id === 'critical'
        ? '🔴 Crisis total activada en todos los equipos'
        : `💚 Recovery: ${data.maintained?.length ?? 0} equipos mantenidos`
      onToast?.(msg)
    }
    setLoading(null)
  }

  return (
    <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 p-4">
      <div className="text-xs uppercase text-slate-500 font-semibold mb-3 flex items-center gap-2">
        <span className="w-1 h-3 bg-purple-500 rounded-full" />
        Controles Demo
      </div>

      {/* Velocidad + Pause/Reset */}
      <div className="flex items-center gap-2 mb-4">
        <button
          onClick={togglePause}
          disabled={loading === 'pause'}
          className={`p-2 rounded-lg border transition-colors ${
            paused
              ? 'bg-emerald-600/20 text-emerald-400 border-emerald-600/40 hover:bg-emerald-600/30'
              : 'bg-slate-700/40 text-slate-300 border-slate-600/40 hover:bg-slate-700/60'
          }`}
        >
          {paused ? <Play size={14} /> : <Pause size={14} />}
        </button>

        <div className="flex-1 flex gap-1">
          {SPEEDS.map(s => (
            <button
              key={s.value}
              onClick={() => setSimSpeed(s.value)}
              disabled={loading === 'speed'}
              className={`flex-1 text-xs py-1.5 rounded border transition-colors ${
                speed === s.value
                  ? 'bg-brand-500/20 text-brand-500 border-brand-500/40'
                  : 'bg-slate-700/30 text-slate-400 border-slate-600/30 hover:bg-slate-700/50'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>

        <button
          onClick={resetPlant}
          disabled={loading === 'reset'}
          className="p-2 rounded-lg border bg-slate-700/40 text-slate-400 border-slate-600/40 hover:text-red-400 hover:border-red-700/40 transition-colors"
          title="Reset planta"
        >
          <RotateCcw size={14} />
        </button>
      </div>

      {/* Escenarios predefinidos */}
      <div className="text-[10px] uppercase text-slate-600 mb-2">Escenarios</div>
      <div className="grid grid-cols-2 gap-2">
        {SCENARIOS.map(sc => (
          <button
            key={sc.id}
            onClick={() => runScenario(sc.id)}
            disabled={loading === sc.id}
            className={`flex items-center justify-center gap-1.5 text-xs py-2 rounded border transition-colors ${sc.color} ${
              loading === sc.id ? 'opacity-50 cursor-wait' : ''
            }`}
          >
            {sc.icon}
            <span>{sc.label}</span>
          </button>
        ))}
      </div>

      {/* Estado actual */}
      <div className="mt-3 pt-3 border-t border-slate-700/30 flex items-center gap-3 text-xs text-slate-500">
        <span className={`flex items-center gap-1 ${paused ? 'text-yellow-400' : 'text-emerald-400'}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${paused ? 'bg-yellow-400' : 'bg-emerald-400 animate-pulse'}`} />
          {paused ? 'Pausado' : 'Corriendo'}
        </span>
        <span>· Velocidad: {speed}×</span>
      </div>
    </div>
  )
}
