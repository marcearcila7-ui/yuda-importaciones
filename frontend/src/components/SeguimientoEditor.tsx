import { useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { FileText, Lock, Save, Ship, Upload } from 'lucide-react'
import { getSeguimiento, guardarSeguimiento, subirBlPdf } from '../api/clientes'
import { useAuthStore } from '../store/authStore'
import { ESTADOS_ENVIO, ESTADOS_VENDEDORA } from '../types/seguimiento'
import type { Hito, Seguimiento } from '../types/seguimiento'

const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'w-full rounded-lg border border-gray-200 px-3 py-2 min-h-[44px] focus:border-[#4B52E8] focus:outline-none'

const ESTADOS_VENDEDORA_SET: ReadonlySet<string> = new Set(ESTADOS_VENDEDORA)

// Editor del seguimiento del envío de una cotización (se usa en Clientes y en Equipo).
// La vendedora gestiona las etapas hasta "en bodega"; la info de envío (naviera,
// tracking, BL) es exclusiva de Marcela (admin).
function SeguimientoEditor({ sesionId }: { sesionId: string }) {
  const { t } = useTranslation()
  const esAdmin = useAuthStore((s) => s.usuario?.rol === 'admin')
  const [estado, setEstado] = useState<string>('cotizacion_enviada')
  const [novedades, setNovedades] = useState('')
  const [tracking, setTracking] = useState('')
  const [naviera, setNaviera] = useState('')
  const [urlTracking, setUrlTracking] = useState('')
  const [eta, setEta] = useState('')
  const [blNumero, setBlNumero] = useState('')
  const [blPdfUrl, setBlPdfUrl] = useState('')
  const [hitos, setHitos] = useState<Record<string, Hito>>({})
  const [trabajando, setTrabajando] = useState(false)
  const [subiendoBl, setSubiendoBl] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const cargar = (s: Seguimiento) => {
    setEstado(s.estado)
    setNovedades(s.novedades ?? '')
    setTracking(s.numero_tracking ?? '')
    setNaviera(s.naviera ?? '')
    setUrlTracking(s.url_tracking ?? '')
    setEta(s.fecha_eta ?? '')
    setBlNumero(s.bl_numero ?? '')
    setBlPdfUrl(s.bl_pdf_url ?? '')
    setHitos(s.hitos ?? {})
  }

  useEffect(() => {
    getSeguimiento(sesionId).then((s) => {
      if (s) cargar(s)
    })
  }, [sesionId])

  const setHito = (key: string, campo: keyof Hito, valor: string) =>
    setHitos((h) => ({ ...h, [key]: { ...h[key], [campo]: valor || null } }))

  // La vendedora no puede tocar el envío una vez está en tránsito (lo movió Marcela).
  const bloqueadaVendedora = !esAdmin && !ESTADOS_VENDEDORA_SET.has(estado)
  // Opciones del desplegable según el rol.
  const opcionesEstado = esAdmin ? ESTADOS_ENVIO : ESTADOS_VENDEDORA

  const subirBl = async (archivo: File) => {
    setSubiendoBl(true)
    try {
      const url = await subirBlPdf(sesionId, archivo)
      setBlPdfUrl(url)
      toast.success(t('envio.blSubido'))
    } catch {
      toast.error(t('envio.errorBl'))
    } finally {
      setSubiendoBl(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

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
        bl_numero: blNumero || null,
        bl_pdf_url: blPdfUrl || null,
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
      {/* Paso 1: etapa actual + su fecha (lo principal para la vendedora) */}
      <div className="rounded-xl border p-4" style={{ borderColor: '#E5E7EB', backgroundColor: '#F9FAFB' }}>
        <p className="mb-1 text-sm font-semibold" style={{ color: '#0D0D0D' }}>
          {t('envio.enQueEtapa')}
        </p>
        {bloqueadaVendedora ? (
          <>
            <div
              className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium"
              style={{ borderColor: '#E5E7EB', backgroundColor: '#FFFFFF', color: '#0D0D0D', minHeight: 44 }}
            >
              {t(`seguimiento.estados.${estado}`)}
            </div>
            <p className="mt-3 flex items-center gap-2 text-sm" style={{ color: '#6B7280' }}>
              <Lock size={15} /> {t('envio.enTransitoMarcela')}
            </p>
          </>
        ) : (
          <>
            <select
              value={estado}
              onChange={(e) => setEstado(e.target.value)}
              style={inputStyle}
              className={inputClase}
            >
              {opcionesEstado.map((k) => (
                <option key={k} value={k}>
                  {t(`seguimiento.estados.${k}`)}
                </option>
              ))}
            </select>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
                {t('envio.fechaDeEtapa')}
                <input
                  type="date"
                  value={hitos[estado]?.fecha ?? ''}
                  onChange={(e) => setHito(estado, 'fecha', e.target.value)}
                  style={inputStyle}
                  className={inputClase}
                />
              </label>
              <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
                {t('seguimiento.notaOpcional')}
                <input
                  value={hitos[estado]?.nota ?? ''}
                  onChange={(e) => setHito(estado, 'nota', e.target.value)}
                  style={inputStyle}
                  className={inputClase}
                />
              </label>
            </div>
          </>
        )}
      </div>

      {/* Novedades para el cliente */}
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

      {/* Información de envío y BL: solo Marcela (admin) */}
      {esAdmin ? (
        <div className="rounded-xl border p-4" style={{ borderColor: '#C7CBF7', backgroundColor: '#EEF0FD' }}>
          <p className="mb-3 flex items-center gap-2 text-sm font-semibold" style={{ color: '#4B52E8' }}>
            <Ship size={16} /> {t('envio.infoEnvioMarcela')}
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
              {t('seguimiento.naviera')}
              <input value={naviera} onChange={(e) => setNaviera(e.target.value)} style={inputStyle} className={inputClase} />
            </label>
            <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
              {t('seguimiento.numeroTracking')}
              <input value={tracking} onChange={(e) => setTracking(e.target.value)} style={inputStyle} className={inputClase} />
            </label>
            <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
              {t('seguimiento.urlTracking')}
              <input value={urlTracking} onChange={(e) => setUrlTracking(e.target.value)} placeholder="https://..." style={inputStyle} className={inputClase} />
            </label>
            <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
              {t('seguimiento.eta')}
              <input type="date" value={eta} onChange={(e) => setEta(e.target.value)} style={inputStyle} className={inputClase} />
            </label>
            <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
              {t('envio.blNumero')}
              <input value={blNumero} onChange={(e) => setBlNumero(e.target.value)} style={inputStyle} className={inputClase} />
            </label>
            <div className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
              {t('envio.blPdf')}
              <div className="flex items-center gap-2">
                <input
                  ref={fileRef}
                  type="file"
                  accept="application/pdf"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0]
                    if (f) subirBl(f)
                  }}
                />
                <button
                  type="button"
                  onClick={() => fileRef.current?.click()}
                  disabled={subiendoBl}
                  className="flex min-h-[44px] flex-1 items-center justify-center gap-2 rounded-lg border border-[#4B52E8] px-3 text-sm font-medium disabled:opacity-60"
                  style={{ color: '#4B52E8' }}
                >
                  <Upload size={16} /> {subiendoBl ? t('envio.subiendo') : t('envio.subirBl')}
                </button>
                {blPdfUrl && (
                  <a
                    href={blPdfUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 text-sm font-medium"
                    style={{ color: '#4B52E8' }}
                  >
                    <FileText size={16} /> {t('envio.verBl')}
                  </a>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2 rounded-xl border border-dashed p-3 text-sm" style={{ borderColor: '#D1D5DB', color: '#6B7280' }}>
          <Lock size={15} /> {t('envio.infoEnvioBloqueada')}
        </div>
      )}

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
