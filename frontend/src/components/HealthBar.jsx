export function HealthBar({ health }) {
  const color = health > 70 ? 'bg-emerald-500' : health > 40 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-slate-400 mb-1">
        <span>Health</span>
        <span className={health > 70 ? 'text-emerald-400' : health > 40 ? 'text-yellow-400' : 'text-red-400'}>
          {health.toFixed(1)}%
        </span>
      </div>
      <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-500`}
          style={{ width: `${Math.max(2, health)}%` }}
        />
      </div>
    </div>
  )
}
