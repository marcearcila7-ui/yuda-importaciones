import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import toast, { Toaster } from 'react-hot-toast'
import GenerarPedidos from '../components/GenerarPedidos/GenerarPedidos'
import Navbar from '../components/Navbar'
import OCRUploader from '../components/OCRUploader/OCRUploader'
import PackingListTable from '../components/PackingListTable/PackingListTable'
import SesionSelector from '../components/SesionSelector/SesionSelector'
import { exportarPackingExcel } from '../api/packing'
import { usePackingStore } from '../store/packingStore'
import type { OCRResultado } from '../types/ocr'
import type { ItemCreate } from '../types/packing'

function Dashboard() {
  const location = useLocation()
  const { sesionActual, items, sesiones, agregarItem, cargarItems, seleccionarSesion, cargarSesiones } =
    usePackingStore()

  // Si se llega desde el Historial con un sesion_id en el state, preseleccionar la sesión
  useEffect(() => {
    const sesionId = (location.state as { sesion_id?: string } | null)?.sesion_id
    if (!sesionId) return
    const preseleccionar = async () => {
      let sesion = sesiones.find((s) => s.id === sesionId)
      if (!sesion) {
        await cargarSesiones()
        sesion = usePackingStore.getState().sesiones.find((s) => s.id === sesionId)
      }
      if (sesion) await seleccionarSesion(sesion)
    }
    preseleccionar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state?.sesion_id])

  // Toma los datos confirmados del OCR y los agrega como ítem del packing list
  const handleItemConfirmado = async (datos: OCRResultado & { foto_url: string }) => {
    const itemCreate: ItemCreate = {
      supplier_nombre: datos.supplier_nombre ?? undefined,
      supplier_numero: datos.supplier_numero ?? undefined,
      foto_url: datos.foto_url,
      descripcion_zh: datos.descripcion_zh ?? undefined,
      qty_por_ctn: datos.qty_por_ctn ?? 1,
      price_rmb: datos.price_rmb ?? 0,
      gw: datos.gw ?? 0,
      largo_cm: datos.largo_cm ?? 0,
      ancho_cm: datos.ancho_cm ?? 0,
      alto_cm: datos.alto_cm ?? 0,
      ctns: 1,
    }
    await agregarItem(itemCreate)
    toast.success('Ítem agregado al Packing List')
  }

  // Descarga el Excel del packing list
  const handleExportar = async () => {
    if (!sesionActual) return
    try {
      const blob = await exportarPackingExcel(sesionActual.id)
      const url = URL.createObjectURL(blob)
      const enlace = document.createElement('a')
      enlace.href = url
      enlace.download = `PackingList_${sesionActual.nombre_cliente}.xlsx`
      enlace.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error('No se pudo exportar el Packing List')
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-100">
      <Toaster position="top-right" />

      <Navbar />

      <main className="flex flex-1 flex-col gap-6 p-4">
        <SesionSelector />

        {sesionActual ? (
          <>
            <OCRUploader onItemConfirmado={handleItemConfirmado} />

            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-800">
                Packing List · {sesionActual.nombre_cliente}
              </h2>
              <button
                type="button"
                onClick={handleExportar}
                style={{ minHeight: 48 }}
                className="rounded bg-green-600 px-4 font-semibold text-white hover:bg-green-700"
              >
                Exportar Packing List
              </button>
            </div>

            <GenerarPedidos
              sesion_id={sesionActual.id}
              nombre_cliente={sesionActual.nombre_cliente}
            />

            <PackingListTable
              items={items}
              sesion_id={sesionActual.id}
              tipo_cambio_usd={sesionActual.tipo_cambio_usd}
              onItemActualizado={cargarItems}
            />
          </>
        ) : (
          <p className="mt-8 text-center text-gray-600">
            Seleccioná o creá una cotización para comenzar
          </p>
        )}
      </main>
    </div>
  )
}

export default Dashboard
