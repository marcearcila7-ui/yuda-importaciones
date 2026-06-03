import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import axios from 'axios'
import toast, { Toaster } from 'react-hot-toast'
import Navbar from '../components/Navbar'
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
const botonStyle: CSSProperties = { minHeight: 48, fontSize: 16 }

type Rol = 'admin' | 'vendedora' | 'contadora'

function mensajeError(err: unknown, generico: string): string {
  if (axios.isAxiosError(err) && err.response?.data?.detail) {
    const d = err.response.data.detail
    return typeof d === 'string' ? d : generico
  }
  return generico
}

function Admin() {
  const [usuarios, setUsuarios] = useState<UsuarioAdmin[]>([])
  const [config, setConfig] = useState<ConfiguracionResponse | null>(null)
  const [cargando, setCargando] = useState(false)

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

  return (
    <div className="relative min-h-screen bg-gray-100">
      <Toaster position="top-right" />
      <Navbar />

      <main className="mx-auto flex max-w-5xl flex-col gap-10 p-4">
        {/* ──────── USUARIOS ──────── */}
        <section>
          <div className="mb-4 flex items-center justify-between">
            <h1 className="text-xl font-semibold text-gray-800">Gestión de usuarios</h1>
            <button
              type="button"
              onClick={() => { setErrorCrear(null); setModalCrear(true) }}
              disabled={cargando}
              style={botonStyle}
              className="rounded bg-blue-700 px-4 font-semibold text-white hover:bg-blue-800 disabled:opacity-60"
            >
              Nuevo usuario
            </button>
          </div>

          <div className="overflow-x-auto rounded border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead className="bg-gray-100 text-left">
                <tr>
                  <th className="px-3 py-2">Nombre</th>
                  <th className="px-3 py-2">Email</th>
                  <th className="px-3 py-2">Rol</th>
                  <th className="px-3 py-2">Estado</th>
                  <th className="px-3 py-2">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {usuarios.map((u) => (
                  <tr key={u.id} className="border-t border-gray-100">
                    <td className="px-3 py-2">{u.nombre}</td>
                    <td className="px-3 py-2">{u.email}</td>
                    <td className="px-3 py-2">{u.rol}</td>
                    <td className="px-3 py-2">
                      <span className={u.activo ? 'text-green-700' : 'text-gray-400'}>
                        {u.activo ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => abrirEditar(u)}
                          disabled={cargando}
                          className="rounded bg-gray-200 px-3 py-1 font-medium text-gray-800 hover:bg-gray-300 disabled:opacity-60"
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          onClick={() => handleToggleActivo(u)}
                          disabled={cargando}
                          className="rounded bg-gray-200 px-3 py-1 font-medium text-gray-800 hover:bg-gray-300 disabled:opacity-60"
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

        {/* ──────── CONFIGURACIÓN ──────── */}
        <section>
          <h1 className="mb-4 text-xl font-semibold text-gray-800">Configuración del sistema</h1>
          <div className="rounded border border-gray-200 bg-white p-4">
            <p className="text-sm text-gray-700">
              Tipo de cambio actual:{' '}
              <span className="font-semibold">{config?.tipo_cambio_usd ?? '—'}</span> RMB/USD
            </p>
            <p className="mb-3 text-xs text-gray-400">
              Última modificación: {config?.updated_at ? new Date(config.updated_at).toLocaleString() : 'sin registro'}
            </p>
            <div className="flex items-end gap-3">
              <label className="flex flex-col gap-1 text-sm text-gray-700">
                Nuevo tipo de cambio
                <input
                  type="number"
                  step="0.01"
                  value={nuevoTC}
                  onChange={(e) => setNuevoTC(e.target.value)}
                  style={inputStyle}
                  className="w-40 rounded border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
                />
              </label>
              <button
                type="button"
                onClick={handleGuardarConfig}
                disabled={cargando}
                style={botonStyle}
                className="rounded bg-green-600 px-4 font-semibold text-white hover:bg-green-700 disabled:opacity-60"
              >
                Guardar
              </button>
            </div>
          </div>
        </section>
      </main>

      {/* ──────── MODAL CREAR ──────── */}
      {modalCrear && (
        <div className="absolute inset-0 z-50 flex items-start justify-center bg-black/40 p-4 pt-20">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-lg">
            <h2 className="mb-4 text-lg font-semibold text-gray-800">Nuevo usuario</h2>
            <div className="flex flex-col gap-3">
              <input style={inputStyle} placeholder="Nombre" value={formCrear.nombre}
                onChange={(e) => setFormCrear({ ...formCrear, nombre: e.target.value })}
                className="rounded border border-gray-300 px-3 py-2" />
              <input style={inputStyle} placeholder="Email" value={formCrear.email}
                onChange={(e) => setFormCrear({ ...formCrear, email: e.target.value })}
                className="rounded border border-gray-300 px-3 py-2" />
              <input style={inputStyle} type="password" placeholder="Contraseña" value={formCrear.password}
                onChange={(e) => setFormCrear({ ...formCrear, password: e.target.value })}
                className="rounded border border-gray-300 px-3 py-2" />
              <select style={inputStyle} value={formCrear.rol}
                onChange={(e) => setFormCrear({ ...formCrear, rol: e.target.value as Rol })}
                className="rounded border border-gray-300 px-3 py-2">
                <option value="admin">admin</option>
                <option value="vendedora">vendedora</option>
                <option value="contadora">contadora</option>
              </select>
              {errorCrear && <p className="text-sm text-red-600">{errorCrear}</p>}
            </div>
            <div className="mt-4 flex gap-3">
              <button type="button" onClick={handleCrear} style={botonStyle}
                className="flex-1 rounded bg-blue-700 px-4 font-semibold text-white hover:bg-blue-800">Crear</button>
              <button type="button" onClick={() => setModalCrear(false)} style={botonStyle}
                className="flex-1 rounded bg-gray-200 px-4 font-semibold text-gray-800 hover:bg-gray-300">Cancelar</button>
            </div>
          </div>
        </div>
      )}

      {/* ──────── MODAL EDITAR ──────── */}
      {editando && (
        <div className="absolute inset-0 z-50 flex items-start justify-center bg-black/40 p-4 pt-20">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-lg">
            <h2 className="mb-4 text-lg font-semibold text-gray-800">Editar usuario</h2>
            <div className="flex flex-col gap-3">
              <input style={inputStyle} placeholder="Nombre" value={formEditar.nombre}
                onChange={(e) => setFormEditar({ ...formEditar, nombre: e.target.value })}
                className="rounded border border-gray-300 px-3 py-2" />
              <select style={inputStyle} value={formEditar.rol}
                onChange={(e) => setFormEditar({ ...formEditar, rol: e.target.value as Rol })}
                className="rounded border border-gray-300 px-3 py-2">
                <option value="admin">admin</option>
                <option value="vendedora">vendedora</option>
                <option value="contadora">contadora</option>
              </select>
              {errorEditar && <p className="text-sm text-red-600">{errorEditar}</p>}
            </div>
            <div className="mt-4 flex flex-col gap-3">
              <div className="flex gap-3">
                <button type="button" onClick={handleGuardarEditar} style={botonStyle}
                  className="flex-1 rounded bg-blue-700 px-4 font-semibold text-white hover:bg-blue-800">Guardar</button>
                <button type="button" onClick={() => setEditando(null)} style={botonStyle}
                  className="flex-1 rounded bg-gray-200 px-4 font-semibold text-gray-800 hover:bg-gray-300">Cancelar</button>
              </div>
              <button type="button"
                onClick={() => { setReseteando(editando); setEditando(null); setNuevaPassword(''); setErrorReset(null) }}
                className="text-sm font-medium text-blue-700 hover:underline">Cambiar contraseña</button>
            </div>
          </div>
        </div>
      )}

      {/* ──────── MODAL RESET CONTRASEÑA ──────── */}
      {reseteando && (
        <div className="absolute inset-0 z-50 flex items-start justify-center bg-black/40 p-4 pt-20">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-lg">
            <h2 className="mb-4 text-lg font-semibold text-gray-800">
              Nueva contraseña · {reseteando.nombre}
            </h2>
            <input style={inputStyle} type="password" placeholder="Nueva contraseña" value={nuevaPassword}
              onChange={(e) => setNuevaPassword(e.target.value)}
              className="w-full rounded border border-gray-300 px-3 py-2" />
            {errorReset && <p className="mt-2 text-sm text-red-600">{errorReset}</p>}
            <div className="mt-4 flex gap-3">
              <button type="button" onClick={handleGuardarReset} style={botonStyle}
                className="flex-1 rounded bg-blue-700 px-4 font-semibold text-white hover:bg-blue-800">Cambiar contraseña</button>
              <button type="button" onClick={() => setReseteando(null)} style={botonStyle}
                className="flex-1 rounded bg-gray-200 px-4 font-semibold text-gray-800 hover:bg-gray-300">Cancelar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Admin
