export function StatusBadge({ status, size = 'sm' }) {
  const cfg = {
    running:     { label: 'OPERATIVO',    cls: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' },
    warning:     { label: 'ALERTA',       cls: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30 pulse-warning' },
    critical:    { label: 'CRÍTICO',      cls: 'bg-red-500/20 text-red-400 border-red-500/30 pulse-critical' },
    maintenance: { label: 'MANTENIMIENTO',cls: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
    stopped:     { label: 'DETENIDO',     cls: 'bg-slate-500/20 text-slate-400 border-slate-500/30' },
  }
  const { label, cls } = cfg[status] || cfg.stopped
  const px = size === 'xs' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-0.5 text-xs'
  return (
    <span className={`${px} font-bold rounded border tracking-wider ${cls}`}>
      {label}
    </span>
  )
}
