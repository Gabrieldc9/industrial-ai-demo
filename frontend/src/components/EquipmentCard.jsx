import { useState } from 'react'
import { Wrench, Zap } from 'lucide-react'
import { StatusBadge } from './StatusBadge'
import { HealthBar } from './HealthBar'
import { SensorSparkline } from './SensorSparkline'

const FAULT_LABELS = {
  bearing_wear: 'Desgaste de rodamiento',
  seal_leak: 'Fuga de sello',
  cavitation: 'Cavitación',
  overload: 'Sobrecarga',
  misalignment: 'Desalineación',
  fouling: 'Incrustación',
  valve_wear: 'Desgaste válvula',
  belt_slip: 'Deslizamiento correa',
  insulation_degradation: 'Degradación aislamiento',
  actuator_fault: 'Falla actuador',
}

export function EquipmentCard({ eq, history, onMaintenance, onInjectFault }) {
  const [expanded, setExpanded] = useState(false)
  const borderColor = {
    running: 'border-emerald-500/20',
    warning: 'border-yellow-500/50',
    critical: 'border-red-500/60',
    maintenance: 'border-blue-500/40',
    stopped: 'border-slate-600',
  }[eq.status] || 'border-slate-700'

  return (
    <div className={`bg-slate-800/60 rounded-xl border ${borderColor} p-4 transition-all duration-300`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-2xl">{eq.icon}</span>
          <div className="min-w-0">
            <div className="font-semibold text-sm text-white truncate">{eq.name}</div>
            <div className="text-xs text-slate-500">{eq.id} · {eq.operating_hours.toFixed(0)}h</div>
          </div>
        </div>
        <StatusBadge status={eq.status} size="xs" />
      </div>

      {/* Health bar */}
      <div className="mb-3">
        <HealthBar health={eq.health} />
      </div>

      {/* Fault badge */}
      {eq.fault_mode && (
        <div className="mb-3 px-2 py-1 bg-red-900/30 border border-red-500/30 rounded text-xs text-red-300">
          ⚠ {FAULT_LABELS[eq.fault_mode] || eq.fault_mode}
        </div>
      )}

      {/* Sensors compactos */}
      <div className="grid grid-cols-2 gap-1.5 mb-3">
        {Object.entries(eq.sensors).slice(0, 4).map(([sensor, val]) => {
          const unit = eq.sensor_units?.[sensor] || ''
          const thresh = eq.thresholds?.[sensor]
          const isLow = ['flow', 'efficiency'].includes(sensor)
          const isCrit = thresh && (isLow ? val < thresh.critical : val > thresh.critical)
          const isWarn = !isCrit && thresh && (isLow ? val < thresh.warning : val > thresh.warning)
          return (
            <div key={sensor} className={`rounded px-2 py-1 text-xs ${
              isCrit ? 'bg-red-900/30 text-red-300' :
              isWarn ? 'bg-yellow-900/30 text-yellow-300' :
              'bg-slate-700/40 text-slate-300'
            }`}>
              <div className="capitalize text-[10px] opacity-60">{sensor}</div>
              <div className="font-mono font-bold">{val.toFixed(1)} {unit}</div>
            </div>
          )
        })}
      </div>

      {/* Sparklines (colapsable) */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-xs text-slate-500 hover:text-slate-300 mb-2 w-full text-left"
      >
        {expanded ? '▲ Ocultar tendencia' : '▼ Ver tendencia'}
      </button>

      {expanded && history && (
        <div className="mb-3 space-y-2">
          {Object.keys(eq.sensors).slice(0, 3).map(sensor => (
            <SensorSparkline
              key={sensor}
              sensor={sensor}
              history={history}
              unit={eq.sensor_units?.[sensor] || ''}
              thresholds={eq.thresholds?.[sensor]}
            />
          ))}
        </div>
      )}

      {/* Acciones */}
      <div className="flex gap-2 pt-2 border-t border-slate-700/50">
        <button
          onClick={() => onMaintenance(eq.id)}
          className="flex-1 flex items-center justify-center gap-1 text-xs py-1.5 rounded bg-blue-600/20 hover:bg-blue-600/40 text-blue-300 border border-blue-500/30 transition-colors"
        >
          <Wrench size={12} /> Mantener
        </button>
        <button
          onClick={() => onInjectFault(eq.id)}
          className="flex-1 flex items-center justify-center gap-1 text-xs py-1.5 rounded bg-orange-600/20 hover:bg-orange-600/40 text-orange-300 border border-orange-500/30 transition-colors"
        >
          <Zap size={12} /> Falla demo
        </button>
      </div>
    </div>
  )
}
