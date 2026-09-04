import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { Check, Tag } from 'lucide-react'
import { guardarShippingMark } from '../../api/packing'

// Marca de embarque de la cotizacion. Identifica la carga de este cliente dentro
// del contenedor, asi que es la misma para todos sus productos: por eso vive en
// la cotizacion y no en cada uno. La pide el formato de la agencia de carga.
function ShippingMark({ sesionId, valorInicial }: { sesionId: string; valorInicial: string }) {
  const { t } = useTranslation()
  const [valor, setValor] = useState(valorInicial)
  const [guardando, setGuardando] = useState(false)
  const [guardado, setGuardado] = useState(false)

  // Al cambiar de cotizacion hay que traer su propia marca
  useEffect(() => {
    setValor(valorInicial)
    setGuardado(false)
  }, [sesionId, valorInicial])

  const guardar = async () => {
    if (valor.trim() === valorInicial.trim()) return
    setGuardando(true)
    try {
      await guardarShippingMark(sesionId, valor.trim())
      setGuardado(true)
      toast.success(t('packing.shippingMarkGuardada'))
    } catch {
      toast.error(t('packing.shippingMarkError'))
    } finally {
      setGuardando(false)
    }
  }

  return (
    <label className="mb-4 flex flex-wrap items-center gap-2 text-sm">
      <span className="flex items-center gap-2" style={{ color: 'var(--yuda-text-secondary)' }}>
        <Tag size={15} /> {t('packing.shippingMark')}
      </span>
      <input
        type="text"
        value={valor}
        onChange={(e) => {
          setValor(e.target.value)
          setGuardado(false)
        }}
        onBlur={guardar}
        placeholder={t('packing.shippingMarkEjemplo')}
        style={{ fontSize: 16, width: 220 }}
        className="rounded-lg border border-gray-200 px-3 py-2 focus:border-[var(--yuda-primary)] focus:outline-none"
      />
      {guardando && <span style={{ color: 'var(--yuda-text-secondary)' }}>…</span>}
      {guardado && !guardando && <Check size={16} style={{ color: 'var(--yuda-success)' }} />}
      <span className="text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
        {t('packing.shippingMarkAyuda')}
      </span>
    </label>
  )
}

export default ShippingMark
