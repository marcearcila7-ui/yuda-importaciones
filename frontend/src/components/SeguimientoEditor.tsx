import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { Save, Ship } from 'lucide-react'
import { getSeguimiento, guardarSeguimiento } from '../api/clientes'
import { ESTADOS_ENVIO } from '../types/seguimiento'
import type { Hito, Seguimiento } from '../types/seguimiento'

const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'w-full rounded-lg border border-gray-200 px-3 py-2 min-h-[44px] focus:border-[#4B52E8] focus:outline-none'

// Editor del seguimiento del envío de una cotización (se usa en el módulo Clientes).
function SeguimientoEditor({ sesionId }: { sesionId: string }) {
  const { t } = useTranslation()
  const [estado, setEstado] = useState<string>('cotizacion_enviada')
  const [novedades, setNovedades] = useState('')
  const [tracking, setTracking] = useState('')
  const [naviera, setNaviera] = useState('')
  const [urlTracking, setUrlTracking] = useState('')
  const [eta, setEta] = useState('')
  const [hitos, setHitos] = useState<Record<string, Hito>>({})
  const [trabajando, setTrabajando] = useState(false)

  const cargar = (s: Seguimiento) => {
    setEstado(s.estado)
    setNovedades(s.novedades ?? '')
    setTracking(s.numero_tracking ?? '')
    setNaviera(s.naviera ?? '')
    setUrlTracking(s.url_tracking ?? '')
    setEta(s.fecha_eta ?? '')
    setHitos(s.hitos ?? {})
  }

  useEffect(() => {
    getSeguimiento(sesionId).then((s) => {
      if (s) cargar(s)
    })
  }, [sesionId])

  const setHito = (key: string, campo: keyof Hito, valor: string) =>
    setHitos((h) => ({ ...h, [key]: { ...h[key], [campo]: valor || null } }))

  const guardar = async () => {
    setTrabajando(true)
    const limpios: Record<string, Hito> = {}
    for (const k of ESTADOS_ENVIO) {
      const h = hitos[k]
      if (h && (h.fecha || h.nota)) limpios[k] = { fecha: h.fecha || null, nota: h.nota || null }
    }
    try {
      const s = await guardarSeguimiento(sesionId, {
        estado,
        novedades: novedades || null,
        numero_tracking: tracking || null,
        naviera: naviera || null,
        url_tracking: urlTracking || null,
        fecha_eta: eta || null,
        hitos: limpios,
      })
      cargar(s)
      toast.success(t('envio.seguimientoGuardado'))
    } catch {
      toast.error(t('envio.errorGuardar'))
    } finally {
      setTrabajando(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
          {t('seguimiento.numeroTracking')}
          <input value={tracking} onChange={(e) => setTracking(e.target.value)} style={inputStyle} className={inputClase} />
        </label>
        <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
          {t('seguimiento.naviera')}
          <input value={naviera} onChange={(e) => setNaviera(e.target.value)} style={inputStyle} className={inputClase} />
        </label>
        <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
          {t('seguimiento.urlTracking')}
          <input value={urlTracking} onChange={(e) => setUrlTracking(e.target.value)} placeholder="https://..." style={inputStyle} className={inputClase} />
        </label>
        <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
          {t('seguimiento.eta')}
          <input type="date" value={eta} onChange={(e) => setEta(e.target.value)} style={inputStyle} className={inputClase} />
        </label>
      </div>

      <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
        {t('seguimiento.novedades')}
        <textarea
          value={novedades}
          onChange={(e) => setNovedades(e.target.value)}
          rows={2}
          style={inputStyle}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 focus:border-[#4B52E8] focus:outline-none"
        />
      </label>

      <div>
        <p className="flex items-center gap-2 text-sm font-semibold" style={{ color: '#0D0D0D' }}>
          <Ship size={16} /> {t('envio.fechasHitos')}
        </p>
        <p className="mb-3 text-xs" style={{ color: '#6B7280' }}>
          {t('envio.etapasAyuda')}
        </p>
        <div className="flex flex-col gap-2">
          {ESTADOS_ENVIO.map((k) => {
            const esActual = estado === k
            return (
              <div
                key={k}
                className="rounded-lg border p-2"
                style={{
                  borderColor: esActual ? '#4B52E8' : '#E5E7EB',
                  backgroundColor: esActual ? '#EEF0FD' : '#FFFFFF',
                }}
              >
                <label className="flex cursor-pointer items-center gap-2">
                  <input
                    type="radio"
                    name={`estado-${sesionId}`}
                    checked={esActual}
                    onChange={() => setEstado(k)}
                  />
                  <span className="text-sm" style={{ fontWeight: esActual ? 700 : 500, color: '#0D0D0D' }}>
                    {t(`seguimiento.estados.${k}`)}
                  </span>
                  {esActual && (
                    <span className="ml-auto text-xs font-semibold" style={{ color: '#4B52E8' }}>
                      {t('envio.etapaActual')}
                    </span>
                  )}
                </label>
                <div className="mt-2 grid gap-2 sm:grid-cols-2">
                  <input
                    type="date"
                    value={hitos[k]?.fecha ?? ''}
                    onChange={(e) => setHito(k, 'fecha', e.target.value)}
                    style={inputStyle}
                    className="rounded-lg border border-gray-200 px-2 py-2 focus:border-[#4B52E8] focus:outline-none"
                  />
                  <input
                    value={hitos[k]?.nota ?? ''}
                    onChange={(e) => setHito(k, 'nota', e.target.value)}
                    placeholder={t('seguimiento.notaOpcional')}
                    style={inputStyle}
                    className="rounded-lg border border-gray-200 px-2 py-2 focus:border-[#4B52E8] focus:outline-none"
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <button
        type="button"
        onClick={guardar}
        disabled={trabajando}
        className="flex items-center justify-center gap-2 font-semibold text-white disabled:opacity-60"
        style={{ minHeight: 48, backgroundColor: '#4B52E8', borderRadius: 8, fontSize: 16 }}
      >
        <Save size={18} /> {t('envio.guardarSeguimiento')}
      </button>
    </div>
  )
}

export default SeguimientoEditor
