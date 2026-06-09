/**
 * PinGuard — protección por PIN para acciones que mutan estado.
 *
 * Uso:
 *   const { protectedFetch } = usePinGuard()
 *   const res = await protectedFetch('/api/plant/reset', { method: 'POST' })
 *   if (!res) return  // usuario canceló
 *
 * Comportamiento:
 *  - Primera acción protegida → modal pide PIN
 *  - PIN correcto → se guarda en sessionStorage para la sesión
 *  - PIN incorrecto (401 del server) → modal reaparece con mensaje de error
 *  - Usuario cancela → protectedFetch retorna null
 */
import { createContext, useContext, useRef, useState, useCallback } from 'react'
import { Lock, Eye, EyeOff } from 'lucide-react'

const PinGuardContext = createContext(null)

export function usePinGuard() {
  const ctx = useContext(PinGuardContext)
  if (!ctx) throw new Error('usePinGuard must be used inside PinGuardProvider')
  return ctx
}

export function PinGuardProvider({ children }) {
  const [modal, setModal] = useState({ open: false, error: false })
  const [inputPin, setInputPin] = useState('')
  const [showPin, setShowPin] = useState(false)
  const resolveRef = useRef(null)
  // Cache PIN en ref (sincronizado con sessionStorage)
  const pinRef = useRef(sessionStorage.getItem('demo_pin') || null)

  /** Abre el modal y devuelve una Promise que resuelve con el PIN o null si cancela. */
  function openModal(withError = false) {
    setInputPin('')
    setShowPin(false)
    setModal({ open: true, error: withError })
    return new Promise(resolve => {
      resolveRef.current = resolve
    })
  }

  function handleSubmit(e) {
    e.preventDefault()
    const pin = inputPin.trim()
    if (!pin) return
    pinRef.current = pin
    sessionStorage.setItem('demo_pin', pin)
    setModal({ open: false, error: false })
    resolveRef.current?.(pin)
    resolveRef.current = null
  }

  function handleCancel() {
    setModal({ open: false, error: false })
    resolveRef.current?.(null)
    resolveRef.current = null
  }

  /**
   * Wrapper de fetch que inyecta X-Demo-Pin.
   * Si el server devuelve 401 → limpia caché y muestra modal de error.
   * Retorna la Response, o null si el usuario canceló.
   */
  const protectedFetch = useCallback(async (url, options = {}) => {
    // Obtener PIN (de caché o modal)
    let pin = pinRef.current
    if (!pin) {
      pin = await openModal(false)
      if (!pin) return null  // cancelado
    }

    const res = await fetch(url, {
      ...options,
      headers: { ...options.headers, 'X-Demo-Pin': pin },
    })

    if (res.status === 401) {
      // PIN incorrecto → limpiar caché y pedir de nuevo
      pinRef.current = null
      sessionStorage.removeItem('demo_pin')
      const newPin = await openModal(true)
      if (!newPin) return null  // cancelado en el retry

      // Reintentar con el nuevo PIN
      return fetch(url, {
        ...options,
        headers: { ...options.headers, 'X-Demo-Pin': newPin },
      })
    }

    return res
  }, [])

  return (
    <PinGuardContext.Provider value={{ protectedFetch }}>
      {children}

      {modal.open && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div
            className="bg-slate-800 border border-slate-600/50 rounded-2xl p-7 w-full max-w-sm shadow-2xl mx-4"
            onClick={e => e.stopPropagation()}
          >
            {/* Ícono + título */}
            <div className="flex flex-col items-center text-center mb-6">
              <div className="w-14 h-14 rounded-2xl bg-brand-500/15 border border-brand-500/30 flex items-center justify-center mb-4">
                <Lock size={24} className="text-brand-500" />
              </div>
              <h2 className="text-white font-semibold text-lg leading-tight">Acción protegida</h2>
              <p className="text-slate-400 text-sm mt-1.5">
                Ingresá el PIN de operador para continuar
              </p>
            </div>

            {/* Mensaje de error */}
            {modal.error && (
              <div className="mb-4 px-3 py-2.5 rounded-lg bg-red-900/30 border border-red-500/40 text-red-300 text-sm text-center">
                PIN incorrecto — intentá de nuevo
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit}>
              <div className="relative mb-4">
                <input
                  autoFocus
                  type={showPin ? 'text' : 'password'}
                  value={inputPin}
                  onChange={e => setInputPin(e.target.value)}
                  placeholder="••••••"
                  className="w-full bg-slate-700/60 border border-slate-600/50 rounded-xl px-4 py-3.5 text-white placeholder-slate-600 focus:outline-none focus:border-brand-500/60 focus:ring-1 focus:ring-brand-500/30 text-center text-xl tracking-[0.3em] font-mono transition-colors"
                  maxLength={30}
                />
                <button
                  type="button"
                  onClick={() => setShowPin(v => !v)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                  tabIndex={-1}
                >
                  {showPin ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>

              <button
                type="submit"
                disabled={!inputPin.trim()}
                className="w-full py-3 rounded-xl bg-brand-500 hover:bg-brand-600 active:bg-brand-700 text-white font-semibold text-sm transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              >
                Confirmar acción
              </button>
            </form>

            <button
              onClick={handleCancel}
              className="w-full mt-3 py-1.5 text-slate-500 hover:text-slate-300 text-sm transition-colors"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}
    </PinGuardContext.Provider>
  )
}
