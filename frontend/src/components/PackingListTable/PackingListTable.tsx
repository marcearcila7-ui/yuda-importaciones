import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from '@tanstack/react-table'
import { useTranslation } from 'react-i18next'
import { usePackingStore } from '../../store/packingStore'
import type { ItemResponse } from '../../types/packing'

interface PackingListTableProps {
  items: ItemResponse[]
  sesion_id: string
  tipo_cambio_usd: number
  onItemActualizado: () => void
}

type Kind = 'text-edit' | 'num-edit' | 'ro-num' | 'photo' | 'unit'

interface ColMeta {
  campo?: keyof ItemResponse
  kind: Kind
  width: number
  stickyLeft?: number
  ctns?: boolean
  usd?: boolean
}

const inputStyle: CSSProperties = { fontSize: 16 }

// Definición de columnas en el orden exacto del Packing List (Tarea 4)
const COLUMNAS: Array<{ id: string; header: string; meta: ColMeta }> = [
  { id: 'supplier_nombre', header: 'SUPPLIER', meta: { campo: 'supplier_nombre', kind: 'text-edit', width: 160, stickyLeft: 0 } },
  { id: 'supplier_numero', header: 'N° STAND', meta: { campo: 'supplier_numero', kind: 'text-edit', width: 100 } },
  { id: 'foto_url', header: 'PHOTO', meta: { campo: 'foto_url', kind: 'photo', width: 60 } },
  { id: 'item_no', header: 'ITEM NO', meta: { campo: 'item_no', kind: 'text-edit', width: 110 } },
  { id: 'descripcion_es', header: 'ESPAÑOL', meta: { campo: 'descripcion_es', kind: 'text-edit', width: 200, stickyLeft: 160 } },
  { id: 'descripcion_en', header: 'ENGLISH', meta: { campo: 'descripcion_en', kind: 'text-edit', width: 200 } },
  { id: 'descripcion_zh', header: '中文', meta: { campo: 'descripcion_zh', kind: 'text-edit', width: 160 } },
  { id: 'material', header: 'MATERIAL', meta: { campo: 'material', kind: 'text-edit', width: 120 } },
  { id: 'uso', header: 'USO', meta: { campo: 'uso', kind: 'text-edit', width: 100 } },
  { id: 'ctns', header: 'CTNS', meta: { campo: 'ctns', kind: 'num-edit', width: 80, ctns: true } },
  { id: 'moq_cajas', header: 'MQT', meta: { campo: 'moq_cajas', kind: 'num-edit', width: 80 } },
  { id: 'qty_por_ctn', header: 'QTY/CTN', meta: { campo: 'qty_por_ctn', kind: 'num-edit', width: 90 } },
  { id: 'unit', header: 'UNIT', meta: { kind: 'unit', width: 70 } },
  { id: 't_qty', header: 'T.QTY', meta: { campo: 't_qty', kind: 'ro-num', width: 90 } },
  { id: 'price_rmb', header: 'PRICE RMB', meta: { campo: 'price_rmb', kind: 'num-edit', width: 100 } },
  { id: 'total_rmb', header: 'TOTAL ¥', meta: { campo: 'total_rmb', kind: 'ro-num', width: 100 } },
  { id: 'price_usd', header: 'PRICE USD', meta: { campo: 'price_usd', kind: 'ro-num', width: 100, usd: true } },
  { id: 'total_usd', header: 'TOTAL USD', meta: { campo: 'total_usd', kind: 'ro-num', width: 100 } },
  { id: 'largo_cm', header: 'L cm', meta: { campo: 'largo_cm', kind: 'num-edit', width: 70 } },
  { id: 'ancho_cm', header: 'W cm', meta: { campo: 'ancho_cm', kind: 'num-edit', width: 70 } },
  { id: 'alto_cm', header: 'H cm', meta: { campo: 'alto_cm', kind: 'num-edit', width: 70 } },
  { id: 'cbm', header: 'CBM', meta: { campo: 'cbm', kind: 'ro-num', width: 90 } },
  { id: 't_cbm', header: 'T.CBM', meta: { campo: 't_cbm', kind: 'ro-num', width: 90 } },
  { id: 'gw', header: 'GW', meta: { campo: 'gw', kind: 'num-edit', width: 70 } },
  { id: 't_gw', header: 'T.GW', meta: { campo: 't_gw', kind: 'ro-num', width: 80 } },
]

const TEXTO: Array<ColMeta['kind']> = ['text-edit']

// Celda editable: click → input → blur/Enter guarda
function CeldaEditable({
  item,
  meta,
  onItemActualizado,
}: {
  item: ItemResponse
  meta: ColMeta
  onItemActualizado: () => void
}) {
  const { t } = useTranslation()
  const actualizarItem = usePackingStore((s) => s.actualizarItem)
  const campo = meta.campo as keyof ItemResponse
  const valorActual = item[campo]
  const [editando, setEditando] = useState(false)
  const [valor, setValor] = useState<string>(valorActual == null ? '' : String(valorActual))
  const [guardando, setGuardando] = useState(false)

  const esTexto = TEXTO.includes(meta.kind)

  const guardar = async () => {
    setEditando(false)
    let nuevoValor: string | number | undefined
    if (esTexto) {
      nuevoValor = valor === '' ? undefined : valor
    } else {
      nuevoValor = valor === '' ? 0 : Number(valor)
      if (Number.isNaN(nuevoValor)) return
    }
    // Si no cambió, no hace nada
    if (String(valorActual ?? '') === String(nuevoValor ?? '')) return
    setGuardando(true)
    await actualizarItem(item.id, { [campo]: nuevoValor })
    setGuardando(false)
    onItemActualizado()
  }

  const fondo = meta.ctns ? { backgroundColor: '#EEF0FD' } : undefined

  if (editando) {
    return (
      <input
        autoFocus
        type={esTexto ? 'text' : 'number'}
        value={valor}
        onChange={(e) => setValor(e.target.value)}
        onBlur={guardar}
        onKeyDown={(e) => {
          if (e.key === 'Enter') guardar()
          if (e.key === 'Escape') setEditando(false)
        }}
        style={{ ...inputStyle, ...fondo }}
        className={`w-full rounded px-1 py-1 outline-none ${
          meta.ctns ? 'border border-blue-400' : 'border border-blue-300'
        }`}
      />
    )
  }

  return (
    <div
      onClick={() => {
        setValor(valorActual == null ? '' : String(valorActual))
        setEditando(true)
      }}
      style={fondo}
      className={`min-h-[28px] cursor-pointer px-1 py-1 ${guardando ? 'opacity-50' : ''} ${
        meta.ctns ? 'border border-blue-300' : ''
      }`}
      title={t('packing.tocaEditar')}
    >
      {guardando ? '…' : valorActual == null || valorActual === '' ? '—' : String(valorActual)}
    </div>
  )
}

// Celda de solo lectura
function CeldaSoloLectura({ item, meta }: { item: ItemResponse; meta: ColMeta }) {
  if (meta.kind === 'unit') {
    return <div className="px-1 py-1 text-center text-gray-600">PCS</div>
  }
  if (meta.kind === 'photo') {
    return item.foto_url ? (
      <img
        src={item.foto_url}
        alt="foto"
        style={{ width: 40, height: 40 }}
        className="rounded object-cover"
      />
    ) : (
      <div style={{ width: 40, height: 40 }} className="rounded bg-gray-200" />
    )
  }
  const valor = item[meta.campo as keyof ItemResponse]
  return (
    <div
      className="px-1 py-1 text-right"
      style={meta.usd ? { color: '#EF4444' } : undefined}
    >
      {valor == null ? '—' : String(valor)}
    </div>
  )
}

// ─── Vista móvil: cada producto como tarjeta con los campos clave ───

type TipoCampo = 'text' | 'num'

function CampoMovil({
  item,
  campo,
  label,
  tipo,
  onSaved,
}: {
  item: ItemResponse
  campo: keyof ItemResponse
  label: string
  tipo: TipoCampo
  onSaved: () => void
}) {
  const actualizarItem = usePackingStore((s) => s.actualizarItem)
  const actual = item[campo]
  const [valor, setValor] = useState<string>(actual == null ? '' : String(actual))
  const [guardando, setGuardando] = useState(false)

  const guardar = async () => {
    let nuevo: string | number | undefined
    if (tipo === 'text') {
      nuevo = valor === '' ? undefined : valor
    } else {
      nuevo = valor === '' ? 0 : Number(valor)
      if (Number.isNaN(nuevo)) return
    }
    if (String(actual ?? '') === String(nuevo ?? '')) return
    setGuardando(true)
    await actualizarItem(item.id, { [campo]: nuevo })
    setGuardando(false)
    onSaved()
  }

  return (
    <label className="flex flex-col gap-1 text-xs" style={{ color: '#6B7280' }}>
      {label}
      <input
        type={tipo === 'text' ? 'text' : 'number'}
        value={valor}
        onChange={(e) => setValor(e.target.value)}
        onBlur={guardar}
        style={{ ...inputStyle, opacity: guardando ? 0.5 : 1 }}
        className="rounded-lg border border-gray-200 px-2 py-2 text-sm focus:border-[#4B52E8] focus:outline-none"
      />
    </label>
  )
}

function TarjetaMovil({
  item,
  onItemActualizado,
}: {
  item: ItemResponse
  onItemActualizado: () => void
}) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-gray-200 p-3">
      <div className="flex gap-3">
        {item.foto_url ? (
          <img src={item.foto_url} alt="" style={{ width: 56, height: 56 }} className="flex-shrink-0 rounded-lg object-cover" />
        ) : (
          <div style={{ width: 56, height: 56 }} className="flex-shrink-0 rounded-lg bg-gray-100" />
        )}
        <div className="min-w-0 flex-1">
          <CampoMovil item={item} campo="supplier_nombre" label={t('packing.fProveedor')} tipo="text" onSaved={onItemActualizado} />
        </div>
      </div>

      <CampoMovil item={item} campo="descripcion_es" label={t('packing.fDescripcion')} tipo="text" onSaved={onItemActualizado} />

      <div className="grid grid-cols-3 gap-2">
        <CampoMovil item={item} campo="ctns" label={t('packing.fCajas')} tipo="num" onSaved={onItemActualizado} />
        <CampoMovil item={item} campo="moq_cajas" label={t('packing.fMqt')} tipo="num" onSaved={onItemActualizado} />
        <CampoMovil item={item} campo="qty_por_ctn" label={t('packing.fUnidCaja')} tipo="num" onSaved={onItemActualizado} />
        <CampoMovil item={item} campo="price_rmb" label={t('packing.fPrecioRmb')} tipo="num" onSaved={onItemActualizado} />
      </div>

      <div className="flex justify-between border-t border-gray-100 pt-2 text-sm">
        <span style={{ color: '#6B7280' }}>{t('packing.fTotalUsd')}</span>
        <span style={{ fontWeight: 700, color: '#0D0D0D' }}>$ {(item.total_usd || 0).toFixed(2)}</span>
      </div>
    </div>
  )
}

function PackingListTable({ items, onItemActualizado }: PackingListTableProps) {
  const { t } = useTranslation()
  // Construye las definiciones de columna para TanStack Table
  const columnas: ColumnDef<ItemResponse>[] = COLUMNAS.map((col) => ({
    id: col.id,
    header: t(`packing.cols.${col.id}`),
    meta: col.meta,
    cell: ({ row }) => {
      const meta = col.meta
      if (meta.kind === 'text-edit' || meta.kind === 'num-edit') {
        return (
          <CeldaEditable
            item={row.original}
            meta={meta}
            onItemActualizado={onItemActualizado}
          />
        )
      }
      return <CeldaSoloLectura item={row.original} meta={meta} />
    },
  }))

  const table = useReactTable({
    data: items,
    columns: columnas,
    getCoreRowModel: getCoreRowModel(),
  })

  // Totales calculados localmente; se recalculan cuando cambian los items
  const [totales, setTotales] = useState({ ctns: 0, total_rmb: 0, total_usd: 0, t_cbm: 0 })
  useEffect(() => {
    setTotales({
      ctns: items.reduce((a, i) => a + (i.ctns || 0), 0),
      total_rmb: items.reduce((a, i) => a + (i.total_rmb || 0), 0),
      total_usd: items.reduce((a, i) => a + (i.total_usd || 0), 0),
      t_cbm: items.reduce((a, i) => a + (i.t_cbm || 0), 0),
    })
  }, [items])

  const estiloCelda = (meta: ColMeta, esHeader: boolean): CSSProperties => {
    const base: CSSProperties = { minWidth: meta.width, width: meta.width }
    if (meta.stickyLeft !== undefined) {
      base.position = 'sticky'
      base.left = meta.stickyLeft
      base.zIndex = esHeader ? 30 : 20
      base.backgroundColor = esHeader ? '#0D0D0D' : '#ffffff'
    }
    return base
  }

  return (
    <>
      {/* Vista móvil: tarjetas */}
      <div className="flex flex-col gap-3 sm:hidden">
        {items.length === 0 ? (
          <p className="py-4 text-center text-sm" style={{ color: '#9CA3AF' }}>
            {t('packing.sinProductos')}
          </p>
        ) : (
          <>
            {items.map((it) => (
              <TarjetaMovil key={it.id} item={it} onItemActualizado={onItemActualizado} />
            ))}
            <div className="flex justify-between rounded-xl px-3 py-3" style={{ backgroundColor: '#0D0D0D' }}>
              <span className="text-sm font-bold text-white">
                {t('packing.totales')} · {totales.ctns} {t('packing.fCajas').toLowerCase()}
              </span>
              <span className="text-sm font-bold text-white">$ {totales.total_usd.toFixed(2)}</span>
            </div>
          </>
        )}
      </div>

      {/* Vista escritorio: tabla completa */}
      <div className="hidden w-full overflow-x-auto rounded border border-gray-200 sm:block">
      <table className="border-collapse text-sm">
        <thead>
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id} style={{ backgroundColor: '#0D0D0D' }}>
              {hg.headers.map((header) => {
                const meta = header.column.columnDef.meta as ColMeta
                return (
                  <th
                    key={header.id}
                    style={estiloCelda(meta, true)}
                    className="whitespace-nowrap border border-gray-500 px-2 py-2 font-bold text-white"
                  >
                    {flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                )
              })}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id} className="bg-white even:bg-gray-50 hover:bg-[#F5F5F0]">
              {row.getVisibleCells().map((cell) => {
                const meta = cell.column.columnDef.meta as ColMeta
                return (
                  <td
                    key={cell.id}
                    style={estiloCelda(meta, false)}
                    className="border border-gray-200 align-middle"
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
        <tfoot className="sticky bottom-0">
          <tr style={{ backgroundColor: '#0D0D0D' }} className="font-bold">
            {COLUMNAS.map((col) => {
              let contenido = ''
              if (col.id === 'supplier_nombre') contenido = `${t('packing.totales')}:`
              else if (col.id === 'ctns') contenido = String(totales.ctns)
              else if (col.id === 'total_rmb') contenido = totales.total_rmb.toFixed(2)
              else if (col.id === 'total_usd') contenido = totales.total_usd.toFixed(2)
              else if (col.id === 't_cbm') contenido = totales.t_cbm.toFixed(6)
              const meta = col.meta
              const estilo = estiloCelda(meta, false)
              estilo.backgroundColor = '#0D0D0D'
              return (
                <td
                  key={col.id}
                  style={estilo}
                  className="border border-gray-700 px-2 py-2 text-right text-white"
                >
                  {contenido}
                </td>
              )
            })}
          </tr>
        </tfoot>
      </table>
      </div>
    </>
  )
}

export default PackingListTable
