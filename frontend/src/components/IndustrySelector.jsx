import { useEffect, useState } from 'react'
import { Factory, ChevronRight, Check } from 'lucide-react'
import { usePinGuard } from '../context/PinGuard'

export function IndustrySelector({ currentIndustryId, onSelect, onClose }) {
  const { protectedFetch } = usePinGuard()
  const [industries, setIndustries] = useState([])
  const [loading, setLoading] = useState(null)

  useEffect(() => {
    fetch('/api/industries').then(r => r.json()).then(setIndustries)
  }, [])

  async function handleSelect(id) {
    if (id === currentIndustryId) { onClose?.(); return }
    setLoading(id)
    const res = await protectedFetch('/api/plant/industry', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ industry_id: id }),
    })
    if (res?.ok) {
      const data = await res.json()
      onSelect?.(data)
    }
    setLoading(null)
  }

  return (
    <div className="fixed inset-0 z-[150] flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-700/60 rounded-2xl p-8 w-full max-w-2xl mx-4 shadow-2xl">

        {/* Header */}
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-brand-500/20 border border-brand-500/30 flex items-center justify-center">
            <Factory size={18} className="text-brand-500" />
          </div>
          <div>
            <h2 className="text-white font-bold text-lg leading-tight">Seleccioná la industria</h2>
            <p className="text-slate-500 text-sm">Cada industria tiene equipos, sensores y KPIs propios</p>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="ml-auto text-slate-500 hover:text-slate-300 text-sm transition-colors"
            >
              Cancelar
            </button>
          )}
        </div>

        <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3">
          {industries.map(ind => {
            const isActive  = ind.id === currentIndustryId
            const isLoading = loading === ind.id

            return (
              <button
                key={ind.id}
                onClick={() => handleSelect(ind.id)}
                disabled={isLoading}
                className={`relative text-left p-5 rounded-xl border transition-all ${
                  isActive
                    ? 'bg-brand-500/10 border-brand-500/40 ring-1 ring-brand-500/30'
                    : 'bg-slate-800/60 border-slate-700/40 hover:border-slate-600/60 hover:bg-slate-800'
                } ${isLoading ? 'opacity-60 cursor-wait' : ''}`}
              >
                {/* Checkmark si es activo */}
                {isActive && (
                  <div className="absolute top-3 right-3 w-5 h-5 rounded-full bg-brand-500/20 border border-brand-500/40 flex items-center justify-center">
                    <Check size={11} className="text-brand-500" />
                  </div>
                )}

                <div className="text-3xl mb-3">{ind.icon}</div>
                <div className="font-semibold text-white text-sm leading-tight mb-1">{ind.name}</div>
                <div className="text-xs text-slate-500 mb-2">{ind.site_name}</div>
                <p className="text-xs text-slate-400 leading-relaxed">{ind.description}</p>

                {!isActive && !isLoading && (
                  <div className="mt-3 flex items-center gap-1 text-xs text-brand-500 font-medium">
                    Seleccionar <ChevronRight size={12} />
                  </div>
                )}
                {isLoading && (
                  <div className="mt-3 text-xs text-slate-400">Cargando...</div>
                )}
                {isActive && (
                  <div className="mt-3 text-xs text-brand-500 font-medium">Activa</div>
                )}
              </button>
            )
          })}
        </div>

        <p className="mt-5 text-center text-xs text-slate-600">
          Cambiar industria resetea la planta y limpia el historial de órdenes de trabajo
        </p>
      </div>
    </div>
  )
}
