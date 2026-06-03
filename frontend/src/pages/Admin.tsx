import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'
import {
  actualizarConfiguracion,
  actualizarUsuario,
  crearUsuario,
  getConfiguracion,
  getUsuarios,
  resetPassword,
} from '../api/admin'
import type { ConfiguracionResponse, UsuarioAdmin } from '../types/admin'

const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'rounded-lg border border-gray-200 px-3 py-2 focus:border-[#4B52E8] focus:outline-none'

type Rol = 'admin' | 'vendedora' | 'contadora'

function mensajeError(err: unknown, generico: string): string {
  if (axios.isAxiosError(err) && err.response?.data?.detail) {
    const d = err.response.data.detail
    return typeof d === 'string' ? d : generico
  }
  return generico
}

// Botones reutilizables
const btnPrimario: CSSProperties = {
  minHeight: 48,
  backgroundColor: '#4B52E8',
  color: '#fff',
  borderRadius: 8,
  padding: '0 20px',
  fontSize: 16,
  fontWeight: 600,
}
const btnSecundario: CSSProperties = {
  minHeight: 48,
  backgroundColor: '#F3F4F6',
  color: '#0D0D0D',
  borderRadius: 8,
  padding: '0 20px',
  fontSize: 16,
  fontWeight: 600,
}

function Admin() {
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

  const cargar = async () => {
    setCargando(true)
    try {
      const [us, cfg] = await Promise.all([getUsuarios(), getConfiguracion()])
      setUsuarios(us)
      setConfig(cfg)
      setNuevoTC(String(cfg.tipo_cambio_usd))
    } catch (err) {
      toast.error(mensajeError(err, 'No se pudieron cargar los datos'))
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    cargar()
  }, [])

  const handleCrear = async () => {
    setErrorCrear(null)
    try {
      await crearUsuario(formCrear)
      setModalCrear(false)
      setFormCrear({ nombre: '', email: '', password: '', rol: 'vendedora' })
      await cargar()
      toast.success('Usuario creado')
    } catch (err) {
      setErrorCrear(mensajeError(err, 'No se pudo crear el usuario'))
    }
  }

  const handleToggleActivo = async (u: UsuarioAdmin) => {
    try {
      await actualizarUsuario(u.id, { activo: !u.activo })
      await cargar()
    } catch (err) {
      toast.error(mensajeError(err, 'No se pudo actualizar el usuario'))
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
      toast.success('Usuario actualizado')
    } catch (err) {
      setErrorEditar(mensajeError(err, 'No se pudo actualizar el usuario'))
    }
  }

  const handleGuardarReset = async () => {
    if (!reseteando) return
    setErrorReset(null)
    try {
      await resetPassword(reseteando.id, nuevaPassword)
      setReseteando(null)
      setNuevaPassword('')
      toast.success('Contraseña actualizada')
    } catch (err) {
      setErrorReset(mensajeError(err, 'No se pudo cambiar la contraseña'))
    }
  }

  const handleGuardarConfig = async () => {
    try {
      const cfg = await actualizarConfiguracion(Number(nuevoTC))
      setConfig(cfg)
      toast.success('Tipo de cambio actualizado')
    } catch (err) {
      toast.error(mensajeError(err, 'No se pudo guardar la configuración'))
    }
  }

  const tabStyle = (activo: boolean): CSSProperties => ({
    padding: '10px 4px',
    marginRight: 24,
    fontWeight: 600,
    fontSize: 15,
    color: activo ? '#4B52E8' : '#6B7280',
    borderBottom: activo ? '3px solid #4B52E8' : '3px solid transparent',
    cursor: 'pointer',
  })

  return (
    <div className="relative flex flex-col gap-6">
      <div>
        <h1 style={{ fontWeight: 700, fontSize: 28, color: '#0D0D0D' }}>Administración</h1>
        <p className="text-sm" style={{ color: '#6B7280' }}>
          Gestión de usuarios y configuración del sistema
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        <button type="button" style={tabStyle(tab === 'usuarios')} onClick={() => setTab('usuarios')}>
          Usuarios
        </button>
        <button type="button" style={tabStyle(tab === 'config')} onClick={() => setTab('config')}>
          Configuración
        </button>
      </div>

      {/* ──────── USUARIOS ──────── */}
      {tab === 'usuarios' && (
        <section className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 style={{ fontWeight: 700, fontSize: 18, color: '#0D0D0D' }}>Gestión de usuarios</h2>
            <button
              type="button"
              onClick={() => { setErrorCrear(null); setModalCrear(true) }}
              disabled={cargando}
              style={btnPrimario}
              className="disabled:opacity-60"
            >
              + Nuevo usuario
            </button>
          </div>

          <div className="card overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead style={{ backgroundColor: '#0D0D0D', color: '#FFFFFF' }}>
                <tr>
                  <th className="px-4 py-3 text-left font-semibold">Nombre</th>
                  <th className="px-4 py-3 text-left font-semibold">Email</th>
                  <th className="px-4 py-3 text-left font-semibold">Rol</th>
                  <th className="px-4 py-3 text-left font-semibold">Estado</th>
                  <th className="px-4 py-3 text-left font-semibold">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {usuarios.map((u, i) => (
                  <tr key={u.id} style={{ backgroundColor: i % 2 === 0 ? '#FFFFFF' : '#F9F9F7' }}>
                    <td className="px-4 py-3 font-medium">{u.nombre}</td>
                    <td className="px-4 py-3">{u.email}</td>
                    <td className="px-4 py-3">{u.rol}</td>
                    <td className="px-4 py-3">
                      <span
                        className="rounded-full px-3 py-1 text-xs font-semibold"
                        style={
                          u.activo
                            ? { backgroundColor: '#D1FAE5', color: '#065F46' }
                            : { backgroundColor: '#F3F4F6', color: '#6B7280' }
                        }
                      >
                        {u.activo ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => abrirEditar(u)}
                          disabled={cargando}
                          className="rounded-lg px-3 py-1 text-sm font-medium disabled:opacity-60"
                          style={{ backgroundColor: '#EEF0FD', color: '#4B52E8' }}
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          onClick={() => handleToggleActivo(u)}
                          disabled={cargando}
                          className="rounded-lg px-3 py-1 text-sm font-medium disabled:opacity-60"
                          style={{ backgroundColor: '#F3F4F6', color: '#0D0D0D' }}
                        >
                          {u.activo ? 'Desactivar' : 'Activar'}
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
          <h2 className="mb-1" style={{ fontWeight: 700, fontSize: 18, color: '#0D0D0D' }}>
            Configuración del sistema
          </h2>
          <p className="text-sm" style={{ color: '#0D0D0D' }}>
            Tipo de cambio actual:{' '}
            <span className="font-bold">{config?.tipo_cambio_usd ?? '—'}</span> RMB/USD
          </p>
          <p className="mb-4 text-xs text-gray-400">
            Última modificación: {config?.updated_at ? new Date(config.updated_at).toLocaleString() : 'sin registro'}
          </p>
          <div className="flex items-end gap-3">
            <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
              Nuevo tipo de cambio
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
              Guardar
            </button>
          </div>
        </section>
      )}

      {/* ──────── MODAL CREAR ──────── */}
      {modalCrear && (
        <div className="absolute inset-0 z-50 flex items-start justify-center bg-black/40 p-4 pt-16">
          <div className="w-full max-w-md bg-white p-6" style={{ borderRadius: 16, boxShadow: '0 10px 30px rgba(0,0,0,0.2)' }}>
            <h2 className="mb-4" style={{ fontWeight: 700, fontSize: 18 }}>Nuevo usuario</h2>
            <div className="flex flex-col gap-3">
              <input style={inputStyle} placeholder="Nombre" value={formCrear.nombre}
                onChange={(e) => setFormCrear({ ...formCrear, nombre: e.target.value })} className={inputClase} />
              <input style={inputStyle} placeholder="Email" value={formCrear.email}
                onChange={(e) => setFormCrear({ ...formCrear, email: e.target.value })} className={inputClase} />
              <input style={inputStyle} type="password" placeholder="Contraseña" value={formCrear.password}
                onChange={(e) => setFormCrear({ ...formCrear, password: e.target.value })} className={inputClase} />
              <select style={inputStyle} value={formCrear.rol}
                onChange={(e) => setFormCrear({ ...formCrear, rol: e.target.value as Rol })} className={inputClase}>
                <option value="admin">admin</option>
                <option value="vendedora">vendedora</option>
                <option value="contadora">contadora</option>
              </select>
              {errorCrear && <p className="text-sm" style={{ color: '#EF4444' }}>{errorCrear}</p>}
            </div>
            <div className="mt-5 flex gap-3">
              <button type="button" onClick={handleCrear} style={{ ...btnPrimario, flex: 1 }}>Crear</button>
              <button type="button" onClick={() => setModalCrear(false)} style={{ ...btnSecundario, flex: 1 }}>Cancelar</button>
            </div>
          </div>
        </div>
      )}

      {/* ──────── MODAL EDITAR ──────── */}
      {editando && (
        <div className="absolute inset-0 z-50 flex items-start justify-center bg-black/40 p-4 pt-16">
          <div className="w-full max-w-md bg-white p-6" style={{ borderRadius: 16, boxShadow: '0 10px 30px rgba(0,0,0,0.2)' }}>
            <h2 className="mb-4" style={{ fontWeight: 700, fontSize: 18 }}>Editar usuario</h2>
            <div className="flex flex-col gap-3">
              <input style={inputStyle} placeholder="Nombre" value={formEditar.nombre}
                onChange={(e) => setFormEditar({ ...formEditar, nombre: e.target.value })} className={inputClase} />
              <select style={inputStyle} value={formEditar.rol}
                onChange={(e) => setFormEditar({ ...formEditar, rol: e.target.value as Rol })} className={inputClase}>
                <option value="admin">admin</option>
                <option value="vendedora">vendedora</option>
                <option value="contadora">contadora</option>
              </select>
              {errorEditar && <p className="text-sm" style={{ color: '#EF4444' }}>{errorEditar}</p>}
            </div>
            <div className="mt-5 flex flex-col gap-3">
              <div className="flex gap-3">
                <button type="button" onClick={handleGuardarEditar} style={{ ...btnPrimario, flex: 1 }}>Guardar</button>
                <button type="button" onClick={() => setEditando(null)} style={{ ...btnSecundario, flex: 1 }}>Cancelar</button>
              </div>
              <button type="button"
                onClick={() => { setReseteando(editando); setEditando(null); setNuevaPassword(''); setErrorReset(null) }}
                className="text-sm font-medium" style={{ color: '#4B52E8' }}>Cambiar contraseña</button>
            </div>
          </div>
        </div>
      )}

      {/* ──────── MODAL RESET CONTRASEÑA ──────── */}
      {reseteando && (
        <div className="absolute inset-0 z-50 flex items-start justify-center bg-black/40 p-4 pt-16">
          <div className="w-full max-w-md bg-white p-6" style={{ borderRadius: 16, boxShadow: '0 10px 30px rgba(0,0,0,0.2)' }}>
            <h2 className="mb-4" style={{ fontWeight: 700, fontSize: 18 }}>
              Nueva contraseña · {reseteando.nombre}
            </h2>
            <input style={inputStyle} type="password" placeholder="Nueva contraseña" value={nuevaPassword}
              onChange={(e) => setNuevaPassword(e.target.value)} className={`w-full ${inputClase}`} />
            {errorReset && <p className="mt-2 text-sm" style={{ color: '#EF4444' }}>{errorReset}</p>}
            <div className="mt-5 flex gap-3">
              <button type="button" onClick={handleGuardarReset} style={{ ...btnPrimario, flex: 1 }}>Cambiar contraseña</button>
              <button type="button" onClick={() => setReseteando(null)} style={{ ...btnSecundario, flex: 1 }}>Cancelar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Admin
