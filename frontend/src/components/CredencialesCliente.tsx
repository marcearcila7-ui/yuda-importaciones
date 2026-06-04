import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { Check, Copy } from 'lucide-react'
import type { ClienteCreado } from '../types/cliente'

// Muestra las credenciales recién creadas + el link del portal, con botón de copiar.
function CredencialesCliente({
  cliente,
  onCerrar,
}: {
  cliente: ClienteCreado
  onCerrar?: () => void
}) {
  const { t } = useTranslation()
  const [copiado, setCopiado] = useState(false)
  const portalUrl = `${window.location.origin}/portal/login`

  const copiar = async () => {
    const texto = `YUDA Importaciones — acceso a tu portal
${t('clientes.portalLink')}: ${portalUrl}
${t('clientes.email')}: ${cliente.email}
${t('clientes.password')}: ${cliente.password_inicial}`
    try {
      await navigator.clipboard.writeText(texto)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2500)
    } catch {
      toast.error(t('clientes.errorCopiar'))
    }
  }

  return (
    <div className="rounded-xl p-4" style={{ backgroundColor: '#F5F5F0', border: '1px solid #10B981' }}>
      <p className="mb-1" style={{ fontWeight: 700, fontSize: 15, color: '#0D0D0D' }}>
        {t('clientes.credencialesTitulo')}
      </p>
      <p className="mb-3 text-sm" style={{ color: '#6B7280' }}>
        {t('clientes.credencialesAviso')}
      </p>
      <div className="grid gap-1 text-sm" style={{ color: '#374151' }}>
        <p>
          <strong>{t('clientes.portalLink')}:</strong>{' '}
          <a href={portalUrl} target="_blank" rel="noreferrer" style={{ color: '#4B52E8' }}>
            {portalUrl}
          </a>
        </p>
        <p>
          <strong>{t('clientes.email')}:</strong> {cliente.email}
        </p>
        <p>
          <strong>{t('clientes.password')}:</strong>{' '}
          <span style={{ fontFamily: 'monospace' }}>{cliente.password_inicial}</span>
        </p>
      </div>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={copiar}
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-white"
          style={{ backgroundColor: '#10B981' }}
        >
          {copiado ? <Check size={16} /> : <Copy size={16} />}{' '}
          {copiado ? t('clientes.copiado') : t('clientes.copiar')}
        </button>
        {onCerrar && (
          <button type="button" onClick={onCerrar} className="rounded-lg px-3 py-2 text-sm font-medium" style={{ color: '#6B7280' }}>
            {t('clientes.cerrar')}
          </button>
        )}
      </div>
    </div>
  )
}

export default CredencialesCliente
