import { LineChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, YAxis } from 'recharts'

export function SensorSparkline({ sensor, history, unit, thresholds }) {
  const data = history.map((snap, i) => ({
    t: i,
    v: snap?.[sensor] ?? null,
  })).filter(d => d.v !== null)

  if (data.length < 2) return null

  const isLow = ['flow', 'efficiency'].includes(sensor)
  const latest = data[data.length - 1]?.v ?? 0
  const isCrit = thresholds && (isLow ? latest < thresholds.critical : latest > thresholds.critical)
  const isWarn = !isCrit && thresholds && (isLow ? latest < thresholds.warning : latest > thresholds.warning)
  const color = isCrit ? '#f87171' : isWarn ? '#fbbf24' : '#34d399'

  return (
    <div>
      <div className="flex justify-between text-[10px] text-slate-500 mb-0.5">
        <span className="capitalize">{sensor}</span>
        <span className={isCrit ? 'text-red-400' : isWarn ? 'text-yellow-400' : 'text-emerald-400'}>
          {latest.toFixed(1)} {unit}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={40}>
        <LineChart data={data}>
          <YAxis domain={['auto', 'auto']} hide />
          {thresholds && (
            <ReferenceLine y={isLow ? thresholds.warning : thresholds.warning} stroke="#fbbf24" strokeDasharray="3 3" strokeOpacity={0.5} />
          )}
          <Line
            type="monotone"
            dataKey="v"
            stroke={color}
            dot={false}
            strokeWidth={1.5}
            isAnimationActive={false}
          />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: 'none', fontSize: 10, padding: '2px 6px' }}
            formatter={(v) => [`${v?.toFixed(2)} ${unit}`, sensor]}
            labelFormatter={() => ''}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
