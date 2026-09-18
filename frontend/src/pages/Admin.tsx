import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'
import { useTranslation } from 'react-i18next'
import { ChevronDown, Trash2 } from 'lucide-react'
import {
  actualizarConfiguracion,
  actualizarUsuario,
  crearUsuario,
  desactivarVendedorasExcepto,
  eliminarUsuario,
  getConfiguracion,
  getUsuarios,
  resetPassword,
} from '../api/admin'
import { desactivarClientesExcepto } from '../api/clientes'
import { confirmar } from '../store/confirmStore'
import type { ConfiguracionResponse, UsuarioAdmin } from '../types/admin'

const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'rounded-lg border border-gray-200 px-3 py-2 focus:border-[var(--yuda-primary)] focus:outline-none'

type Rol = 'admin' | 'vendedora' | 'contadora' | 'bodega'

function mensajeError(err: unknown, generico: string): string {
  if (axios.isAxiosError(err) && err.response?.data?.detail) {
    const d = err.response.data.detail
    return typeof d === 'string' ? d : generico
  }
  return generico
}

const btnPrimario: CSSProperties = {
  minHeight: 48,
  backgroundColor: 'var(--yuda-primary)',
  color: '#fff',
  borderRadius: 8,
  padding: '0 20px',
  fontSize: 16,
  fontWeight: 600,
}
const btnSecundario: CSSProperties = {
  minHeight: 48,
  backgroundColor: '#F3F4F6',
  color: 'var(--yuda-accent)',
  borderRadius: 8,
  padding: '0 20px',
  fontSize: 16,
  fontWeight: 600,
}

function Admin() {
  const { t } = useTranslation()
  const [usuarios, setUsuarios] = useState<UsuarioAdmin[]>([])
  const [config, setConfig] = useState<ConfiguracionResponse | null>(null)
  const [cargando, setCargando] = useState(false)
  const [tab, setTab] = useState<'usuarios' | 'config'>('usuarios')

  // Modal crear
  const [modalCrear, setModalCrear] = useState(false)
  const [formCrear, setFormCrear] = useState({ nombre: '', email: '', password: '', rol: 'vendedora' as Rol })
  const [errorCrear, setErrorCrear] = useState<string | null>(null)

  // Modal editar
  const [editando, setEditando] = useState<UsuarioAdmin | null>(null)
  const [formEditar, setFormEditar] = useState({ nombre: '', rol: 'vendedora' as Rol })
  const [errorEditar, setErrorEditar] = useState<string | null>(null)

  // Modal reset contraseña
  const [reseteando, setReseteando] = useState<UsuarioAdmin | null>(null)
  const [nuevaPassword, setNuevaPassword] = useState('')
  const [errorReset, setErrorReset] = useState<string | null>(null)

  // Configuración
  const [nuevoTC, setNuevoTC] = useState('')

  // Limpieza masiva (empezar de cero): elegir a quiénes NO tocar
  const [mostrarLimpieza, setMostrarLimpieza] = useState(false)
  const [mantenerIds, setMantenerIds] = useState<Set<string>>(new Set())
  const [limpiando, setLimpiando] = useState(false)

  const cargar = async () => {
    setCargando(true)
    try {
      const [us, cfg] = await Promise.all([getUsuarios(), getConfiguracion()])
      setUsuarios(us)
      setConfig(cfg)
      setNuevoTC(String(cfg.tipo_cambio_usd))
    } catch (err) {
      toast.error(mensajeError(err, t('admin.errorCargar')))
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    cargar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleCrear = async () => {
    setErrorCrear(null)
    try {
      await crearUsuario(formCrear)
      setModalCrear(false)
      setFormCrear({ nombre: '', email: '', password: '', rol: 'vendedora' })
      await cargar()
      toast.success(t('admin.usuarioCreado'))
    } catch (err) {
      setErrorCrear(mensajeError(err, t('admin.errorCrear')))
    }
  }

  const handleToggleActivo = async (u: UsuarioAdmin) => {
    try {
      await actualizarUsuario(u.id, { activo: !u.activo })
      await cargar()
    } catch (err) {
      toast.error(mensajeError(err, t('admin.errorActualizar')))
    }
  }

  // Borra de verdad, no solo desactiva. El backend rechaza (409) si el
  // usuario ya tiene cotizaciones/clientes/compras, y ese mensaje explica
  // qué hacer en su lugar (desactivar) — se muestra tal cual.
  const handleEliminar = async (u: UsuarioAdmin) => {
    const ok = await confirmar({
      mensaje: t('admin.confirmarEliminarUsuario', { nombre: u.nombre }),
      peligro: true,
      textoConfirmar: t('admin.eliminar'),
    })
    if (!ok) return
    try {
      await eliminarUsuario(u.id)
      toast.success(t('admin.usuarioEliminado'))
      await cargar()
    } catch (err) {
      toast.error(mensajeError(err, t('admin.errorEliminar')))
    }
  }

  const toggleMantener = (id: string) =>
    setMantenerIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const vendedorasActivas = usuarios.filter((u) => u.rol === 'vendedora')
  const nombresAMantener = vendedorasActivas
    .filter((v) => mantenerIds.has(v.id))
    .map((v) => v.nombre)
    .join(', ')

  const handleDesactivarVendedoras = async () => {
    const ok = await confirmar({
      mensaje: t('admin.confirmarDesactivarVendedoras', { nombres: nombresAMantener || '—' }),
      peligro: true,
      textoConfirmar: t('admin.desactivar'),
    })
    if (!ok) return
    setLimpiando(true)
    try {
      const { desactivadas } = await desactivarVendedorasExcepto(Array.from(mantenerIds))
      toast.success(t('admin.vendedorasDesactivadas', { n: desactivadas }))
      await cargar()
    } catch (err) {
      toast.error(mensajeError(err, t('admin.errorLimpieza')))
    } finally {
      setLimpiando(false)
    }
  }

  const handleOcultarClientes = async () => {
    const ok = await confirmar({
      mensaje: t('admin.confirmarOcultarClientes', { nombres: nombresAMantener || '—' }),
      peligro: true,
      textoConfirmar: t('admin.ocultar'),
    })
    if (!ok) return
    setLimpiando(true)
    try {
      const { desactivados } = await desactivarClientesExcepto(Array.from(mantenerIds))
      toast.success(t('admin.clientesOcultados', { n: desactivados }))
    } catch (err) {
      toast.error(mensajeError(err, t('admin.errorLimpieza')))
    } finally {
      setLimpiando(false)
    }
  }

  const abrirEditar = (u: UsuarioAdmin) => {
    setEditando(u)
    setFormEditar({ nombre: u.nombre, rol: u.rol })
    setErrorEditar(null)
  }

  const handleGuardarEditar = async () => {
    if (!editando) return
    setErrorEditar(null)
    try {
      await actualizarUsuario(editando.id, { nombre: formEditar.nombre, rol: formEditar.rol })
      setEditando(null)
      await cargar()
      toast.success(t('admin.usuarioActualizado'))
    } catch (err) {
      setErrorEditar(mensajeError(err, t('admin.errorActualizar')))
    }
  }

  const handleGuardarReset = async () => {
    if (!reseteando) return
    setErrorReset(null)
    try {
      await resetPassword(reseteando.id, nuevaPassword)
      setReseteando(null)
      setNuevaPassword('')
      toast.success(t('admin.contrasenaActualizada'))
    } catch (err) {
      setErrorReset(mensajeError(err, t('admin.errorContrasena')))
    }
  }

  const handleGuardarConfig = async () => {
    try {
      const cfg = await actualizarConfiguracion(Number(nuevoTC))
      setConfig(cfg)
      toast.success(t('admin.tipoCambioActualizado'))
    } catch (err) {
      toast.error(mensajeError(err, t('admin.errorConfig')))
    }
  }

  const tabStyle = (activo: boolean): CSSProperties => ({
    padding: '10px 4px',
    marginRight: 24,
    fontWeight: 600,
    fontSize: 15,
    color: activo ? 'var(--yuda-primary)' : 'var(--yuda-text-secondary)',
    borderBottom: activo ? '3px solid var(--yuda-primary)' : '3px solid transparent',
    cursor: 'pointer',
  })

  return (
    <div className="relative flex flex-col gap-6">
      <div>
        <h1 style={{ fontWeight: 700, fontSize: 28, color: 'var(--yuda-accent)' }}>{t('admin.titulo')}</h1>
        <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('admin.subtitulo')}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        <button type="button" style={tabStyle(tab === 'usuarios')} onClick={() => setTab('usuarios')}>
          {t('admin.usuarios')}
        </button>
        <button type="button" style={tabStyle(tab === 'config')} onClick={() => setTab('config')}>
          {t('admin.configuracion')}
        </button>
      </div>

      {/* ──────── USUARIOS ──────── */}
      {tab === 'usuarios' && (
        <section className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>{t('admin.gestionUsuarios')}</h2>
            <button
              type="button"
              onClick={() => { setErrorCrear(null); setModalCrear(true) }}
              disabled={cargando}
              style={btnPrimario}
              className="disabled:opacity-60"
            >
              + {t('admin.nuevoUsuario')}
            </button>
          </div>

          {/* Limpieza inicial: ocultar de la UI (sin borrar nada) a quienes no
              se van a seguir usando, para empezar de cero. */}
          <div className="card">
            <button
              type="button"
              onClick={() => setMostrarLimpieza((v) => !v)}
              className="flex w-full items-center justify-between text-left"
            >
              <span style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
                {t('admin.limpiezaTitulo')}
              </span>
              <ChevronDown
                size={18}
                style={{ transform: mostrarLimpieza ? 'rotate(180deg)' : 'none', color: 'var(--yuda-text-secondary)' }}
              />
            </button>
            {mostrarLimpieza && (
              <div className="mt-4 flex flex-col gap-4">
                <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                  {t('admin.limpiezaAyuda')}
                </p>
                <div className="flex flex-wrap gap-2">
                  {vendedorasActivas.map((v) => (
                    <label
                      key={v.id}
                      className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm"
                      style={{
                        borderColor: mantenerIds.has(v.id) ? 'var(--yuda-primary)' : 'var(--yuda-border)',
                        backgroundColor: mantenerIds.has(v.id) ? 'var(--yuda-primary-soft)' : 'transparent',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={mantenerIds.has(v.id)}
                        onChange={() => toggleMantener(v.id)}
                      />
                      {v.nombre}
                    </label>
                  ))}
                  {vendedorasActivas.length === 0 && (
                    <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                      {t('admin.sinVendedoras')}
                    </p>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={handleDesactivarVendedoras}
                    disabled={mantenerIds.size === 0 || limpiando}
                    className="rounded-lg px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
                    style={{ backgroundColor: 'var(--yuda-error)' }}
                  >
                    {t('admin.desactivarResto')}
                  </button>
                  <button
                    type="button"
                    onClick={handleOcultarClientes}
                    disabled={mantenerIds.size === 0 || limpiando}
                    className="rounded-lg px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
                    style={{ backgroundColor: 'var(--yuda-error)' }}
                  >
                    {t('admin.ocultarClientesResto')}
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="card overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead style={{ backgroundColor: 'var(--yuda-accent)', color: 'var(--yuda-white)' }}>
                <tr>
                  <th className="px-4 py-3 text-left font-semibold">{t('admin.nombre')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('admin.email')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('admin.rol')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('admin.estado')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('admin.acciones')}</th>
                </tr>
              </thead>
              <tbody>
                {usuarios.map((u, i) => (
                  <tr key={u.id} style={{ backgroundColor: i % 2 === 0 ? 'var(--yuda-white)' : '#F9F9F7' }}>
                    <td className="px-4 py-3 font-medium">{u.nombre}</td>
                    <td className="px-4 py-3">{u.email}</td>
                    <td className="px-4 py-3">{t(`roles.${u.rol}`)}</td>
                    <td className="px-4 py-3">
                      <span
                        className="rounded-full px-3 py-1 text-xs font-semibold"
                        style={
                          u.activo
                            ? { backgroundColor: 'var(--yuda-success-soft)', color: 'var(--yuda-success-dark)' }
                            : { backgroundColor: '#F3F4F6', color: 'var(--yuda-text-secondary)' }
                        }
                      >
                        {u.activo ? t('admin.activo') : t('admin.inactivo')}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => abrirEditar(u)}
                          disabled={cargando}
                          className="rounded-lg px-3 py-1 text-sm font-medium disabled:opacity-60"
                          style={{ backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }}
                        >
                          {t('admin.editar')}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleToggleActivo(u)}
                          disabled={cargando}
                          className="rounded-lg px-3 py-1 text-sm font-medium disabled:opacity-60"
                          style={{ backgroundColor: '#F3F4F6', color: 'var(--yuda-accent)' }}
                        >
                          {u.activo ? t('admin.desactivar') : t('admin.activar')}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleEliminar(u)}
                          disabled={cargando}
                          aria-label={t('admin.eliminar')}
                          title={t('admin.eliminar')}
                          className="rounded-lg p-1.5 disabled:opacity-60"
                          style={{ backgroundColor: '#FEF2F2', color: 'var(--yuda-error)' }}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* ──────── CONFIGURACIÓN ──────── */}
      {tab === 'config' && (
        <section className="card max-w-xl">
          <h2 className="mb-1" style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>
            {t('admin.configSistema')}
          </h2>
          <p className="text-sm" style={{ color: 'var(--yuda-accent)' }}>
            {t('admin.tipoCambioActual')}{' '}
            <span className="font-bold">{config?.tipo_cambio_usd ?? '—'}</span> RMB/USD
          </p>
          <p className="mb-4 text-xs text-gray-500">
            {t('admin.ultimaModificacion')}{' '}
            {config?.updated_at ? new Date(config.updated_at).toLocaleString() : t('admin.sinRegistro')}
          </p>
          <div className="flex items-end gap-3">
            <label className="flex flex-col gap-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('admin.tipoCambio')}
              <input
                type="number"
                step="0.01"
                value={nuevoTC}
                onChange={(e) => setNuevoTC(e.target.value)}
                style={inputStyle}
                className={`w-40 ${inputClase}`}
              />
            </label>
            <button type="button" onClick={handleGuardarConfig} disabled={cargando} style={btnPrimario} className="disabled:opacity-60">
              {t('admin.guardar')}
            </button>
          </div>
        </section>
      )}

      {/* ──────── MODAL CREAR ──────── */}
      {modalCrear && (
        <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/40 p-4">
          <div className="w-full max-w-md bg-white p-6" style={{ borderRadius: 16, boxShadow: '0 10px 30px rgba(0,0,0,0.2)' }}>
            <h2 className="mb-4" style={{ fontWeight: 700, fontSize: 18 }}>{t('admin.nuevoUsuario')}</h2>
            <div className="flex flex-col gap-3">
              <input style={inputStyle} placeholder={t('admin.nombre')} value={formCrear.nombre}
                onChange={(e) => setFormCrear({ ...formCrear, nombre: e.target.value })} className={inputClase} />
              <input style={inputStyle} placeholder={t('admin.email')} value={formCrear.email}
                onChange={(e) => setFormCrear({ ...formCrear, email: e.target.value })} className={inputClase} />
              <input style={inputStyle} type="password" placeholder={t('admin.contrasena')} value={formCrear.password}
                onChange={(e) => setFormCrear({ ...formCrear, password: e.target.value })} className={inputClase} />
              <select style={inputStyle} value={formCrear.rol}
                onChange={(e) => setFormCrear({ ...formCrear, rol: e.target.value as Rol })} className={inputClase}>
                <option value="admin">{t('roles.admin')}</option>
                <option value="vendedora">{t('roles.vendedora')}</option>
                <option value="contadora">{t('roles.contadora')}</option>
                <option value="bodega">{t('roles.bodega')}</option>
              </select>
              {errorCrear && <p className="text-sm" style={{ color: 'var(--yuda-error)' }}>{errorCrear}</p>}
            </div>
            <div className="mt-5 flex gap-3">
              <button type="button" onClick={handleCrear} style={{ ...btnPrimario, flex: 1 }}>{t('admin.crear')}</button>
              <button type="button" onClick={() => setModalCrear(false)} style={{ ...btnSecundario, flex: 1 }}>{t('admin.cancelar')}</button>
            </div>
          </div>
        </div>
      )}

      {/* ──────── MODAL EDITAR ──────── */}
      {editando && (
        <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/40 p-4">
          <div className="w-full max-w-md bg-white p-6" style={{ borderRadius: 16, boxShadow: '0 10px 30px rgba(0,0,0,0.2)' }}>
            <h2 className="mb-4" style={{ fontWeight: 700, fontSize: 18 }}>{t('admin.editarUsuario')}</h2>
            <div className="flex flex-col gap-3">
              <input style={inputStyle} placeholder={t('admin.nombre')} value={formEditar.nombre}
                onChange={(e) => setFormEditar({ ...formEditar, nombre: e.target.value })} className={inputClase} />
              <select style={inputStyle} value={formEditar.rol}
                onChange={(e) => setFormEditar({ ...formEditar, rol: e.target.value as Rol })} className={inputClase}>
                <option value="admin">{t('roles.admin')}</option>
                <option value="vendedora">{t('roles.vendedora')}</option>
                <option value="contadora">{t('roles.contadora')}</option>
                <option value="bodega">{t('roles.bodega')}</option>
              </select>
              {errorEditar && <p className="text-sm" style={{ color: 'var(--yuda-error)' }}>{errorEditar}</p>}
            </div>
            <div className="mt-5 flex flex-col gap-3">
              <div className="flex gap-3">
                <button type="button" onClick={handleGuardarEditar} style={{ ...btnPrimario, flex: 1 }}>{t('admin.guardar')}</button>
                <button type="button" onClick={() => setEditando(null)} style={{ ...btnSecundario, flex: 1 }}>{t('admin.cancelar')}</button>
              </div>
              <button type="button"
                onClick={() => { setReseteando(editando); setEditando(null); setNuevaPassword(''); setErrorReset(null) }}
                className="text-sm font-medium" style={{ color: 'var(--yuda-primary)' }}>{t('admin.cambiarContrasena')}</button>
            </div>
          </div>
        </div>
      )}

      {/* ──────── MODAL RESET CONTRASEÑA ──────── */}
      {reseteando && (
        <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/40 p-4">
          <div className="w-full max-w-md bg-white p-6" style={{ borderRadius: 16, boxShadow: '0 10px 30px rgba(0,0,0,0.2)' }}>
            <h2 className="mb-4" style={{ fontWeight: 700, fontSize: 18 }}>
              {t('admin.nuevaContrasena')} · {reseteando.nombre}
            </h2>
            <input style={inputStyle} type="password" placeholder={t('admin.nuevaContrasena')} value={nuevaPassword}
              onChange={(e) => setNuevaPassword(e.target.value)} className={`w-full ${inputClase}`} />
            {errorReset && <p className="mt-2 text-sm" style={{ color: 'var(--yuda-error)' }}>{errorReset}</p>}
            <div className="mt-5 flex gap-3">
              <button type="button" onClick={handleGuardarReset} style={{ ...btnPrimario, flex: 1 }}>{t('admin.cambiarContrasena')}</button>
              <button type="button" onClick={() => setReseteando(null)} style={{ ...btnSecundario, flex: 1 }}>{t('admin.cancelar')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Admin
