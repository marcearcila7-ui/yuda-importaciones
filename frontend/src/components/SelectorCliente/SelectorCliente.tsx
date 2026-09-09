import { useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, Search } from 'lucide-react'
import type { Cliente } from '../../types/cliente'

const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'rounded-lg border border-gray-200 px-3 py-2 focus:border-[var(--yuda-primary)] focus:outline-none'

// A partir de esta cantidad de clientes la lista se vuelve incómoda de recorrer
// a ojo y aparece el buscador.
const CLIENTES_PARA_BUSCADOR = 6

// Fila de cliente guardado
function FilaCliente({
  cliente,
  activo,
  onClick,
}: {
  cliente: Cliente
  activo: boolean
  onClick: () => void
}) {
  const inicial = (cliente.nombre || '?').trim().charAt(0).toUpperCase()
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center gap-3 text-left transition-colors"
      style={{
        minHeight: 56,
        padding: '8px 12px',
        borderRadius: 10,
        border: `1px solid ${activo ? 'var(--yuda-primary)' : 'var(--yuda-border)'}`,
        backgroundColor: activo ? 'var(--yuda-primary-soft)' : 'var(--yuda-white)',
      }}
    >
      <span
        className="flex items-center justify-center font-bold"
        style={{
          width: 34,
          height: 34,
          flexShrink: 0,
          borderRadius: 999,
          fontSize: 14,
          backgroundColor: 'var(--yuda-primary)',
          color: 'var(--yuda-white)',
        }}
      >
        {inicial}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate" style={{ fontWeight: 600, fontSize: 15, color: 'var(--yuda-accent)' }}>
          {cliente.nombre}
        </span>
        <span className="block truncate text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {cliente.empresa ? `${cliente.empresa}, ${cliente.email}` : cliente.email}
        </span>
      </span>
      {activo && <Check size={18} style={{ color: 'var(--yuda-primary)', flexShrink: 0 }} />}
    </button>
  )
}

// Elegir un cliente ya guardado: buscador (si hace falta) + lista de tarjetas.
// Antes esto se veía distinto en cada pantalla donde hacía falta elegir un
// cliente (acá tarjetas con buscador, en ClienteEnvio un <select> simple):
// dos formas de la misma decisión se sentían como que el sistema no era
// consistente consigo mismo. Ahora es un solo componente, un solo lugar donde
// mantenerlo.
function SelectorCliente({
  clientes,
  valor,
  onElegir,
}: {
  clientes: Cliente[]
  valor: string
  onElegir: (id: string) => void
}) {
  const { t } = useTranslation()
  const [busqueda, setBusqueda] = useState('')

  const clientesFiltrados = useMemo(() => {
    const texto = busqueda.trim().toLowerCase()
    if (!texto) return clientes
    return clientes.filter((c) =>
      `${c.nombre} ${c.email} ${c.empresa ?? ''}`.toLowerCase().includes(texto),
    )
  }, [clientes, busqueda])

  return (
    <div className="flex flex-col gap-3">
      {clientes.length >= CLIENTES_PARA_BUSCADOR && (
        <div className="relative">
          <Search
            size={16}
            className="absolute"
            style={{ left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--yuda-text-secondary)' }}
          />
          <input
            type="text"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder={t('dashboard.buscarCliente')}
            style={{ ...inputStyle, paddingLeft: 36 }}
            className={`${inputClase} min-h-[44px] w-full`}
          />
        </div>
      )}

      <div className="flex flex-col gap-2" style={{ maxHeight: 280, overflowY: 'auto' }}>
        {clientesFiltrados.map((c) => (
          <FilaCliente
            key={c.id}
            cliente={c}
            activo={c.id === valor}
            onClick={() => onElegir(c.id)}
          />
        ))}
        {clientesFiltrados.length === 0 && (
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('dashboard.sinResultados', { texto: busqueda })}
          </p>
        )}
      </div>
    </div>
  )
}

export default SelectorCliente
