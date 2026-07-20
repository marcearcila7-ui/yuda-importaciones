import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ChevronRight, Wallet } from 'lucide-react'
import { getClientes } from '../api/clientes'
import type { Cliente } from '../types/cliente'

// Lista de clientes para que la contadora (o el admin) entre a gestionar cada
// estado de cuenta. El detalle vive en /clientes/:id/cuenta.
function Cuentas() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [clientes, setClientes] = useState<Cliente[] | null>(null)

  useEffect(() => {
    getClientes().then(setClientes).catch(() => setClientes([]))
  }, [])

  return (
    <div className="flex flex-col gap-4 p-4 sm:p-6">
      <div>
        <h1 style={{ fontWeight: 700, fontSize: 24, color: 'var(--yuda-accent)' }} className="flex items-center gap-2">
          <Wallet size={22} /> {t('cuentas.titulo')}
        </h1>
        <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('cuentas.subtitulo')}</p>
      </div>

      {clientes && clientes.length === 0 ? (
        <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('cuentas.sinClientes')}</p>
      ) : (
        <div className="flex flex-col gap-2">
          {(clientes ?? []).map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => navigate(`/clientes/${c.id}/cuenta`)}
              className="card flex items-center justify-between text-left"
              style={{ cursor: 'pointer' }}
            >
              <div>
                <div style={{ fontWeight: 600, color: 'var(--yuda-text)' }}>{c.nombre}</div>
                <div className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                  {[c.empresa, c.nit ? `${t('cuenta.nit')}: ${c.nit}` : null].filter(Boolean).join(' · ')}
                </div>
              </div>
              <ChevronRight size={18} style={{ color: 'var(--yuda-primary)' }} />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default Cuentas
