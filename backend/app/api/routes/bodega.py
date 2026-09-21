import logging
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.imagen_valida import detectar_tipo_imagen
from app.database import get_db
from app.models.cliente import Cliente
from app.models.item import Item
from app.models.item_inspeccion import ItemInspeccionBodega
from app.models.pedido import PedidoGenerado, PedidoGeneradoItem
from app.models.seguimiento import ESTADO_INICIAL, ESTADOS_ENVIO, SeguimientoPedido
from app.models.sesion import Sesion
from app.models.pedido_bodega_actividad import PedidoBodegaActividad
from app.models.user import RolUsuario, User
from app.schemas.bodega import (
    ActividadBodegaResponse,
    ActualizarTelefonoInput,
    AsignarPedidoInput,
    BodegaPedidoDetalle,
    BodegaPedidoResumen,
    GuardarOrdenRealInput,
    OrdenGenerada,
    OrdenGeneradaItem,
    UsuarioBodegaBasico,
)
from app.schemas.inspeccion import GuardarInspeccionInput, InspeccionSesionResponse
from app.schemas.portal import PortalItem
from app.schemas.seguimiento import SeguimientoResponse
from app.services.actividad_bodega_service import registrar_actividad_bodega
from app.services.cotizacion_service import _calcular
from app.services.excel_service import generar_csv_pedido, generar_formato_pedido
from app.services.imagen_service import bytes_a_data_uri, convertir_a_jpeg, descargar_imagenes
from app.services.inspeccion_service import construir_inspeccion_sesion, guardar_inspeccion
from app.services.notificacion_service import avisar_inspeccion_actualizada, avisar_orden_actualizada_bodega
from app.services.pdf_service import html_pedido, render_pdf
from app.services.storage_service import borrar_archivos, ruta_desde_url, subir_csv, subir_excel, subir_foto, subir_pdf, subir_video

router = APIRouter(prefix="/bodega", tags=["bodega"])
logger = logging.getLogger("app.bodega")


def _numero(sesion: Sesion) -> str:
    return f"YUDA-{sesion.fecha:%Y%m%d}-{sesion.id[:6].upper()}"


# Evidencia de inspección: fotos (mismos formatos que el resto de la app) y
# video, ambos con límite generoso porque son fotos/videos de celular tal cual.
TIPOS_PERMITIDOS_FOTO_INSPECCION = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
}
DECLARADOS_HEIC_INSPECCION = {"image/heic", "image/heif", "image/heic-sequence", "image/heif-sequence"}
MAX_BYTES_FOTO_INSPECCION = 25 * 1024 * 1024
MAX_FOTOS_INSPECCION = 4

TIPOS_PERMITIDOS_VIDEO = {"video/mp4": ".mp4", "video/quicktime": ".mov", "video/webm": ".webm"}
MAX_BYTES_VIDEO = 100 * 1024 * 1024


async def _leer_y_validar_foto_inspeccion(foto: UploadFile) -> tuple[bytes, str]:
    if foto.content_type not in TIPOS_PERMITIDOS_FOTO_INSPECCION and foto.content_type not in DECLARADOS_HEIC_INSPECCION:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Solo se permiten imágenes JPG, PNG o WEBP")
    imagen_bytes = await foto.read()
    if len(imagen_bytes) > MAX_BYTES_FOTO_INSPECCION:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La imagen no debe superar 25MB")
    tipo_real = detectar_tipo_imagen(imagen_bytes)
    if tipo_real not in TIPOS_PERMITIDOS_FOTO_INSPECCION:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El archivo no es una imagen JPG, PNG o WEBP válida")
    if tipo_real == "image/heic":
        convertida = convertir_a_jpeg(imagen_bytes)
        if convertida is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "No se pudo leer la foto del iPhone. Vuelve a intentarlo."
            )
        imagen_bytes = convertida
        tipo_real = "image/jpeg"
    return imagen_bytes, tipo_real


async def _leer_y_validar_video(video: UploadFile) -> tuple[bytes, str]:
    if video.content_type not in TIPOS_PERMITIDOS_VIDEO:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Solo se permiten videos MP4, MOV o WEBM")
    video_bytes = await video.read()
    if len(video_bytes) > MAX_BYTES_VIDEO:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El video no debe superar 100MB")
    return video_bytes, video.content_type


def _sesion_o_404(db: Session, sesion_id: str) -> Sesion:
    sesion = db.query(Sesion).filter(Sesion.id == sesion_id).first()
    if sesion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cotización no encontrada")
    return sesion


def _item_de_sesion_o_404(db: Session, sesion_id: str, item_id: str) -> Item:
    item = db.query(Item).filter(Item.id == item_id, Item.sesion_id == sesion_id).first()
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado en esta cotización")
    return item


class _ItemCantidadReal:
    """Envuelve un Item usando la cantidad que bodega contó al recibir, para
    reutilizar el mismo generador de Excel/PDF/CSV del pedido (que lee
    `.ctns`) sin tocar el valor pedido original en la base de datos."""

    def __init__(self, item: Item, ctns: int, cantidad_recibida: int | None) -> None:
        self._item = item
        self.ctns = ctns
        self.cantidad_recibida = cantidad_recibida

    def __getattr__(self, nombre: str):
        return getattr(self._item, nombre)


@router.get("/usuarios", response_model=list[UsuarioBodegaBasico])
def listar_usuarios_bodega(
    usuario: User = Depends(require_roles("admin", "vendedora", "bodega")),
    db: Session = Depends(get_db),
) -> list[UsuarioBodegaBasico]:
    """Admin y bodega activos, para el selector de a quién asignar un pedido
    (lo usan tanto Yuda Logistic como la vendedora al enviar a bodega)."""
    usuarios = (
        db.query(User)
        .filter(User.rol.in_([RolUsuario.admin, RolUsuario.bodega]), User.activo)
        .order_by(User.nombre.asc())
        .all()
    )
    return [UsuarioBodegaBasico(id=u.id, nombre=u.nombre) for u in usuarios]


@router.get("/pedidos", response_model=list[BodegaPedidoResumen])
def listar_pedidos_bodega(
    vista: str = "sin_asignar",
    usuario: User = Depends(require_roles("admin", "bodega")),
    db: Session = Depends(get_db),
) -> list[BodegaPedidoResumen]:
    """Cola de bodega, en 3 vistas para que varias personas se repartan el
    trabajo sin pisarse: "sin_asignar" (nadie lo tomó todavía, lo ven todos),
    "asignados" (ya alguien lo tomó, se ve a quién) y "revisado" (ya se marcó
    como recibido y listo para envío)."""
    if vista not in ("sin_asignar", "asignados", "revisado"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Vista inválida")
    estado = "en_bodega" if vista == "revisado" else "proveedor_recibio"

    # OJO: no filtrar por Sesion.pedido_confirmado_at. Ese campo se borra si el
    # cliente vuelve a su portal y reenvía cantidades (aunque sea después de
    # que la vendedora ya mandó el pedido a bodega), y eso NO deshace el envío
    # a bodega — solo dejaba el pedido invisible acá sin ningún aviso. Lo único
    # que de verdad indica que bodega debe verlo es la etapa del seguimiento.
    filas = (
        db.query(Sesion, SeguimientoPedido, User)
        .join(SeguimientoPedido, SeguimientoPedido.sesion_id == Sesion.id)
        .outerjoin(User, User.id == Sesion.user_id)
        .filter(SeguimientoPedido.estado == estado)
        .order_by(SeguimientoPedido.updated_at.asc())
        .all()
    )
    if vista == "sin_asignar":
        filas = [f for f in filas if f[1].bodega_asignado_a_id is None]
    elif vista == "asignados":
        filas = [f for f in filas if f[1].bodega_asignado_a_id is not None]

    asignado_ids = {seg.bodega_asignado_a_id for _, seg, _ in filas if seg.bodega_asignado_a_id}
    asignados_por_id = (
        {u.id: u for u in db.query(User).filter(User.id.in_(asignado_ids)).all()} if asignado_ids else {}
    )

    resultado: list[BodegaPedidoResumen] = []
    for sesion, seg, vendedora in filas:
        total_items = db.query(Item).filter(Item.sesion_id == sesion.id).count()
        ordenes = db.query(PedidoGenerado).filter(PedidoGenerado.sesion_id == sesion.id).all()
        asignado = asignados_por_id.get(seg.bodega_asignado_a_id) if seg.bodega_asignado_a_id else None
        resultado.append(
            BodegaPedidoResumen(
                sesion_id=sesion.id,
                numero=_numero(sesion),
                nombre_cliente=sesion.nombre_cliente,
                fecha=sesion.fecha,
                total_items=total_items,
                total_ordenes=len(ordenes),
                ordenes_revisadas=sum(1 for o in ordenes if o.revisado_en_bodega_at is not None),
                pedido_confirmado_at=sesion.pedido_confirmado_at,
                estado_envio=seg.estado,
                vendedora_nombre=vendedora.nombre if vendedora else None,
                bodega_asignado_a_id=seg.bodega_asignado_a_id,
                bodega_asignado_a_nombre=asignado.nombre if asignado else None,
            )
        )
    return resultado


@router.patch("/pedidos/{sesion_id}/asignar", response_model=BodegaPedidoResumen)
def asignar_pedido_bodega(
    sesion_id: str,
    datos: AsignarPedidoInput,
    usuario: User = Depends(require_roles("admin", "bodega")),
    db: Session = Depends(get_db),
) -> BodegaPedidoResumen:
    """Toma un pedido para sí (auto-asignación) o se lo pasa a otra persona de
    bodega. `asignado_a_id=None` lo vuelve a dejar sin asignar, disponible
    para cualquiera."""
    sesion = _sesion_o_404(db, sesion_id)
    seg = db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == sesion_id).first()
    if seg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Este pedido todavía no tiene seguimiento")

    asignado = None
    if datos.asignado_a_id:
        asignado = (
            db.query(User)
            .filter(User.id == datos.asignado_a_id, User.rol.in_([RolUsuario.admin, RolUsuario.bodega]), User.activo)
            .first()
        )
        if asignado is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ese usuario no es válido para asignarle un pedido")

    seg.bodega_asignado_a_id = asignado.id if asignado else None
    seg.bodega_asignado_en = datetime.now(timezone.utc) if asignado else None
    seg.bodega_asignado_por_id = usuario.id if asignado else None

    detalle = f"Asignado a {asignado.nombre}" if asignado else "Se quitó la asignación"
    registrar_actividad_bodega(db, sesion_id, usuario.id, "asignado", detalle)
    db.commit()

    total_items = db.query(Item).filter(Item.sesion_id == sesion_id).count()
    ordenes = db.query(PedidoGenerado).filter(PedidoGenerado.sesion_id == sesion_id).all()
    vendedora = db.query(User).filter(User.id == sesion.user_id).first()
    return BodegaPedidoResumen(
        sesion_id=sesion.id,
        numero=_numero(sesion),
        nombre_cliente=sesion.nombre_cliente,
        fecha=sesion.fecha,
        total_items=total_items,
        total_ordenes=len(ordenes),
        ordenes_revisadas=sum(1 for o in ordenes if o.revisado_en_bodega_at is not None),
        pedido_confirmado_at=sesion.pedido_confirmado_at,
        estado_envio=seg.estado,
        vendedora_nombre=vendedora.nombre if vendedora else None,
        bodega_asignado_a_id=seg.bodega_asignado_a_id,
        bodega_asignado_a_nombre=asignado.nombre if asignado else None,
    )


@router.get("/pedidos/{sesion_id}", response_model=BodegaPedidoDetalle)
def detalle_pedido_bodega(
    sesion_id: str,
    usuario: User = Depends(require_roles("admin", "bodega")),
    db: Session = Depends(get_db),
) -> BodegaPedidoDetalle:
    """Detalle de un pedido para que bodega lo compare contra la orden de compra:
    cantidades confirmadas, orden de compra adjunta y pedidos ya generados al
    proveedor."""
    sesion = db.query(Sesion).filter(Sesion.id == sesion_id).first()
    if sesion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cotización no encontrada")

    items = db.query(Item).filter(Item.sesion_id == sesion_id).order_by(Item.orden.asc()).all()
    portal_items: list[PortalItem] = []
    for i in items:
        calc = _calcular(i, sesion.tipo_cambio_usd)
        portal_items.append(
            PortalItem(
                item_id=i.id,
                foto_url=i.foto_url,
                referencia=i.referencia,
                descripcion_es=i.descripcion_es,
                descripcion_en=i.descripcion_en,
                descripcion_zh=i.descripcion_zh,
                ctns=i.ctns or 0,
                qty_por_ctn=i.qty_por_ctn or 0,
                t_qty=calc["t_qty"],
                price_usd=calc["price_usd"],
                total_usd=calc["total_usd"],
                cbm=calc["cbm"],
                t_cbm=calc["t_cbm"],
                cantidad_solicitada=i.cantidad_solicitada,
            )
        )

    pedidos_generados = (
        db.query(PedidoGenerado)
        .filter(PedidoGenerado.sesion_id == sesion_id)
        .order_by(PedidoGenerado.fecha_generacion.desc())
        .all()
    )

    seg = db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == sesion_id).first()
    seguimiento = (
        SeguimientoResponse.model_validate(seg) if seg else SeguimientoResponse(estado=ESTADO_INICIAL)
    )

    cliente = (
        db.query(Cliente).filter(Cliente.id == sesion.cliente_id).first()
        if sesion.cliente_id
        else None
    )
    vendedora = db.query(User).filter(User.id == sesion.user_id).first()
    asignado = (
        db.query(User).filter(User.id == seg.bodega_asignado_a_id).first()
        if seg and seg.bodega_asignado_a_id
        else None
    )

    actividad_filas = (
        db.query(PedidoBodegaActividad, User)
        .outerjoin(User, User.id == PedidoBodegaActividad.usuario_id)
        .filter(PedidoBodegaActividad.sesion_id == sesion_id)
        .order_by(PedidoBodegaActividad.created_at.desc())
        .all()
    )
    actividad = [
        ActividadBodegaResponse(
            usuario_nombre=u.nombre if u else None, tipo=a.tipo, detalle=a.detalle, created_at=a.created_at
        )
        for a, u in actividad_filas
    ]

    return BodegaPedidoDetalle(
        sesion_id=sesion.id,
        numero=_numero(sesion),
        nombre_cliente=sesion.nombre_cliente,
        fecha=sesion.fecha,
        items=portal_items,
        notas_cliente=sesion.notas_cliente,
        pedidos_generados=pedidos_generados,
        seguimiento=seguimiento,
        cliente_nombre=cliente.nombre if cliente else None,
        cliente_telefono=cliente.telefono if cliente else None,
        vendedora_nombre=vendedora.nombre if vendedora else None,
        vendedora_email=vendedora.email if vendedora else None,
        bodega_asignado_a_id=asignado.id if asignado else None,
        bodega_asignado_a_nombre=asignado.nombre if asignado else None,
        actividad=actividad,
    )


@router.get("/pedidos/{sesion_id}/ordenes", response_model=list[OrdenGenerada])
def listar_ordenes_bodega(
    sesion_id: str,
    usuario: User = Depends(require_roles("admin", "bodega")),
    db: Session = Depends(get_db),
) -> list[OrdenGenerada]:
    """Las órdenes que se le mandaron a cada proveedor/tienda para esta
    cotización, con sus líneas (cantidad pedida y, si bodega ya la revisó,
    cantidad recibida) para comparar contra lo que llegó."""
    sesion = db.query(Sesion).filter(Sesion.id == sesion_id).first()
    if sesion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cotización no encontrada")

    ordenes = (
        db.query(PedidoGenerado)
        .filter(PedidoGenerado.sesion_id == sesion_id)
        .order_by(PedidoGenerado.supplier.asc())
        .all()
    )

    resultado: list[OrdenGenerada] = []
    for orden in ordenes:
        lineas = (
            db.query(PedidoGeneradoItem, Item)
            .join(Item, Item.id == PedidoGeneradoItem.item_id)
            .filter(PedidoGeneradoItem.pedido_generado_id == orden.id)
            .all()
        )
        resultado.append(
            OrdenGenerada(
                pedido_generado_id=orden.id,
                supplier=orden.supplier,
                fecha_generacion=orden.fecha_generacion,
                archivo_xlsx_url=orden.archivo_xlsx_url,
                archivo_pdf_url=orden.archivo_pdf_url,
                archivo_csv_url=orden.archivo_csv_url,
                archivo_real_xlsx_url=orden.archivo_real_xlsx_url,
                archivo_real_pdf_url=orden.archivo_real_pdf_url,
                archivo_real_csv_url=orden.archivo_real_csv_url,
                revisado_en_bodega_at=orden.revisado_en_bodega_at,
                items=[
                    OrdenGeneradaItem(
                        item_id=item.id,
                        referencia=item.referencia,
                        descripcion_es=item.descripcion_es,
                        descripcion_en=item.descripcion_en,
                        foto_url=item.foto_final_url or item.foto_url,
                        qty_por_ctn=item.qty_por_ctn or 0,
                        cantidad_pedida=linea.cantidad_pedida,
                        cantidad_recibida=linea.cantidad_recibida,
                        nota=linea.nota,
                    )
                    for linea, item in lineas
                ],
            )
        )
    return resultado


@router.put("/pedidos/{sesion_id}/ordenes/{pedido_generado_id}", response_model=OrdenGenerada)
def guardar_orden_real(
    sesion_id: str,
    pedido_generado_id: str,
    datos: GuardarOrdenRealInput,
    usuario: User = Depends(require_roles("admin", "bodega")),
    db: Session = Depends(get_db),
) -> OrdenGenerada:
    """Bodega guarda lo que realmente contó de esta orden al proveedor.
    Regenera el mismo archivo (Excel/PDF/CSV) con las cantidades reales y le
    avisa a la vendedora que ya puede revisarlo."""
    sesion = db.query(Sesion).filter(Sesion.id == sesion_id).first()
    if sesion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cotización no encontrada")
    orden = (
        db.query(PedidoGenerado)
        .filter(PedidoGenerado.id == pedido_generado_id, PedidoGenerado.sesion_id == sesion_id)
        .first()
    )
    if orden is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Orden no encontrada")

    lineas = (
        db.query(PedidoGeneradoItem)
        .filter(PedidoGeneradoItem.pedido_generado_id == pedido_generado_id)
        .all()
    )
    lineas_por_item = {linea.item_id: linea for linea in lineas}
    ids_validos = set(lineas_por_item)
    ids_recibidos = {d.item_id for d in datos.items}
    if not ids_recibidos.issubset(ids_validos):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Alguno de los ítems no pertenece a esta orden"
        )

    for dato in datos.items:
        if dato.cantidad_recibida < 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "La cantidad recibida no puede ser negativa")
        linea = lineas_por_item[dato.item_id]
        linea.cantidad_recibida = dato.cantidad_recibida
        linea.nota = dato.nota

    registrar_actividad_bodega(
        db, sesion_id, usuario.id, "orden_actualizada",
        f"Guardó cantidades reales de la orden a «{orden.supplier}»",
    )

    # Las cantidades/notas se guardan YA, sin importar lo que pase después con
    # los archivos: si la generación falla, bodega no debe perder lo que
    # acaba de escribir y tener que volver a contar todo.
    db.commit()

    # Solo se regenera el archivo si bodega ya contó TODOS los ítems de la
    # orden; a medio llenar, el documento saldría incompleto y confundiría a
    # la vendedora más que ayudarla.
    if all(linea.cantidad_recibida is not None for linea in lineas):
        try:
            items_por_id = {
                i.id: i
                for i in db.query(Item).filter(Item.id.in_([l.item_id for l in lineas])).all()
            }
            items_reales = [
                _ItemCantidadReal(items_por_id[linea.item_id], linea.cantidad_recibida, linea.cantidad_recibida)
                for linea in lineas
            ]
            fecha_hoy = date.today()
            supplier_nombre = items_reales[0].supplier_nombre
            supplier_numero = items_reales[0].supplier_numero

            urls_fotos = [
                (getattr(i, "foto_final_url", None) or getattr(i, "foto_url", None)) for i in items_reales
            ]
            fotos_bytes = descargar_imagenes(urls_fotos, lado_px=900)
            fotos_datauri = {url: bytes_a_data_uri(b) for url, b in fotos_bytes.items()}

            excel_bytes = generar_formato_pedido(
                supplier_nombre, supplier_numero, items_reales, fecha_hoy,
                fotos=fotos_bytes, shipping_mark=sesion.shipping_mark,
            )
            html = html_pedido(
                supplier_nombre, supplier_numero, items_reales, fecha_hoy,
                fotos=fotos_datauri, shipping_mark=sesion.shipping_mark,
            )
            pdf_bytes = render_pdf(html)
            csv_bytes = generar_csv_pedido(
                supplier_nombre, supplier_numero, items_reales, fecha_hoy, con_cantidad_recibida=True
            )

            ruta = f"{sesion_id}/{fecha_hoy:%Y%m%d}_{orden.supplier}_Real"
            orden.archivo_real_xlsx_url = subir_excel(excel_bytes, f"{ruta}.xlsx")
            orden.archivo_real_pdf_url = subir_pdf(pdf_bytes, f"{ruta}.pdf")
            orden.archivo_real_csv_url = subir_csv(csv_bytes, f"{ruta}.csv")
            orden.revisado_en_bodega_at = datetime.now(timezone.utc)
            avisar_orden_actualizada_bodega(
                db, sesion_id, _numero(sesion), sesion.nombre_cliente, sesion.user_id, orden.supplier
            )
            db.commit()
        except Exception:
            db.rollback()
            logger.exception(
                "No se pudo regenerar/guardar el archivo real de la orden %s (sesión %s)",
                pedido_generado_id, sesion_id,
            )
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                "Las cantidades quedaron guardadas, pero no se pudo generar o subir el archivo "
                "con lo que realmente llegó. Vuelve a darle a «Guardar» en unos minutos para "
                "reintentar solo esa parte.",
            )

    lineas_actualizadas = (
        db.query(PedidoGeneradoItem, Item)
        .join(Item, Item.id == PedidoGeneradoItem.item_id)
        .filter(PedidoGeneradoItem.pedido_generado_id == pedido_generado_id)
        .all()
    )
    return OrdenGenerada(
        pedido_generado_id=orden.id,
        supplier=orden.supplier,
        fecha_generacion=orden.fecha_generacion,
        archivo_xlsx_url=orden.archivo_xlsx_url,
        archivo_pdf_url=orden.archivo_pdf_url,
        archivo_csv_url=orden.archivo_csv_url,
        archivo_real_xlsx_url=orden.archivo_real_xlsx_url,
        archivo_real_pdf_url=orden.archivo_real_pdf_url,
        archivo_real_csv_url=orden.archivo_real_csv_url,
        revisado_en_bodega_at=orden.revisado_en_bodega_at,
        items=[
            OrdenGeneradaItem(
                item_id=item.id,
                referencia=item.referencia,
                descripcion_es=item.descripcion_es,
                descripcion_en=item.descripcion_en,
                foto_url=item.foto_final_url or item.foto_url,
                qty_por_ctn=item.qty_por_ctn or 0,
                cantidad_pedida=linea.cantidad_pedida,
                cantidad_recibida=linea.cantidad_recibida,
                nota=linea.nota,
            )
            for linea, item in lineas_actualizadas
        ],
    )


@router.patch("/pedidos/{sesion_id}/cliente-telefono")
def actualizar_telefono_cliente(
    sesion_id: str,
    datos: ActualizarTelefonoInput,
    usuario: User = Depends(require_roles("admin", "bodega")),
    db: Session = Depends(get_db),
) -> dict:
    """Bodega confirma o corrige el teléfono de WhatsApp del cliente antes de
    marcar la mercancía como recibida, para que el aviso de aprobación le
    llegue al número correcto."""
    sesion = db.query(Sesion).filter(Sesion.id == sesion_id).first()
    if sesion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cotización no encontrada")
    if not sesion.cliente_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Esta cotización no está vinculada a un cliente del portal"
        )
    cliente = db.query(Cliente).filter(Cliente.id == sesion.cliente_id).first()
    if cliente is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")

    telefono = datos.telefono.strip()
    if not telefono:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El teléfono no puede quedar vacío")

    cliente.telefono = telefono
    db.commit()
    return {"telefono": cliente.telefono}


@router.get("/pedidos/{sesion_id}/cotizacion", response_model=InspeccionSesionResponse)
def obtener_cotizacion_inspeccion(
    sesion_id: str,
    usuario: User = Depends(require_roles("admin", "bodega")),
    db: Session = Depends(get_db),
) -> InspeccionSesionResponse:
    """Cotización del cliente para que bodega la inspeccione: cada campo trae
    el valor original (el que cargó la vendedora) y el corregido por bodega,
    si acaso."""
    sesion = _sesion_o_404(db, sesion_id)
    return construir_inspeccion_sesion(db, sesion)


@router.put("/pedidos/{sesion_id}/cotizacion", response_model=InspeccionSesionResponse)
def guardar_cotizacion_inspeccion(
    sesion_id: str,
    datos: GuardarInspeccionInput,
    usuario: User = Depends(require_roles("admin", "bodega")),
    db: Session = Depends(get_db),
) -> InspeccionSesionResponse:
    """Guarda las correcciones de bodega sobre la cotización (cantidades
    reales, medidas, descripciones, confirmación de referencia). Nunca toca
    el Item original: el cliente no ve nada de esto, solo la vendedora."""
    sesion = _sesion_o_404(db, sesion_id)
    guardar_inspeccion(db, sesion, datos, usuario)
    registrar_actividad_bodega(db, sesion_id, usuario.id, "inspeccion_actualizada", "Corrigió la cotización del cliente")

    cliente = (
        db.query(Cliente).filter(Cliente.id == sesion.cliente_id).first() if sesion.cliente_id else None
    )
    avisar_inspeccion_actualizada(
        db, sesion.id, _numero(sesion), cliente.nombre if cliente else sesion.nombre_cliente, sesion.user_id
    )
    db.commit()

    return construir_inspeccion_sesion(db, sesion)


@router.post("/pedidos/{sesion_id}/cotizacion/items/{item_id}/fotos")
async def agregar_foto_inspeccion(
    sesion_id: str,
    item_id: str,
    foto: UploadFile,
    usuario: User = Depends(require_roles("admin", "bodega")),
    db: Session = Depends(get_db),
) -> dict:
    """Agrega una foto de evidencia a un producto (máx. 4). No es la foto del
    catálogo del cliente: es aparte, solo para bodega y la vendedora."""
    _sesion_o_404(db, sesion_id)
    item = _item_de_sesion_o_404(db, sesion_id, item_id)

    insp = db.query(ItemInspeccionBodega).filter(ItemInspeccionBodega.item_id == item.id).first()
    fotos_actuales = list(insp.fotos or []) if insp else []
    if len(fotos_actuales) >= MAX_FOTOS_INSPECCION:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Máximo {MAX_FOTOS_INSPECCION} fotos por producto")

    imagen_bytes, tipo_real = await _leer_y_validar_foto_inspeccion(foto)
    extension = TIPOS_PERMITIDOS_FOTO_INSPECCION[tipo_real]
    nombre_archivo = f"inspeccion/{item.id}/{uuid.uuid4().hex}{extension}"
    url = subir_foto(imagen_bytes, nombre_archivo, tipo_real)

    if insp is None:
        insp = ItemInspeccionBodega(item_id=item.id)
        db.add(insp)
    insp.fotos = fotos_actuales + [url]
    insp.actualizado_en = datetime.now(timezone.utc)
    insp.actualizado_por_id = usuario.id
    db.commit()

    return {"fotos": insp.fotos}


@router.delete("/pedidos/{sesion_id}/cotizacion/items/{item_id}/fotos")
def quitar_foto_inspeccion(
    sesion_id: str,
    item_id: str,
    url: str,
    usuario: User = Depends(require_roles("admin", "bodega")),
    db: Session = Depends(get_db),
) -> dict:
    _sesion_o_404(db, sesion_id)
    item = _item_de_sesion_o_404(db, sesion_id, item_id)
    insp = db.query(ItemInspeccionBodega).filter(ItemInspeccionBodega.item_id == item.id).first()
    if insp is None or not insp.fotos or url not in insp.fotos:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esa foto no existe")

    insp.fotos = [f for f in insp.fotos if f != url]
    insp.actualizado_en = datetime.now(timezone.utc)
    insp.actualizado_por_id = usuario.id
    db.commit()
    borrar_archivos("fotos", [ruta_desde_url(url, "fotos")])

    return {"fotos": insp.fotos}


@router.post("/pedidos/{sesion_id}/cotizacion/items/{item_id}/video")
async def subir_video_inspeccion(
    sesion_id: str,
    item_id: str,
    video: UploadFile,
    usuario: User = Depends(require_roles("admin", "bodega")),
    db: Session = Depends(get_db),
) -> dict:
    """Sube (o reemplaza) el video de evidencia de un producto. Un solo video
    por producto: si ya había uno, se borra el anterior."""
    _sesion_o_404(db, sesion_id)
    item = _item_de_sesion_o_404(db, sesion_id, item_id)

    video_bytes, content_type = await _leer_y_validar_video(video)
    extension = TIPOS_PERMITIDOS_VIDEO[content_type]
    nombre_archivo = f"inspeccion/{item.id}/{uuid.uuid4().hex}{extension}"
    url = subir_video(video_bytes, nombre_archivo, content_type)

    insp = db.query(ItemInspeccionBodega).filter(ItemInspeccionBodega.item_id == item.id).first()
    if insp is None:
        insp = ItemInspeccionBodega(item_id=item.id)
        db.add(insp)
    url_anterior = insp.video_url
    insp.video_url = url
    insp.actualizado_en = datetime.now(timezone.utc)
    insp.actualizado_por_id = usuario.id
    db.commit()
    if url_anterior:
        borrar_archivos("pedidos", [ruta_desde_url(url_anterior, "pedidos")])

    return {"video_url": insp.video_url}


@router.delete("/pedidos/{sesion_id}/cotizacion/items/{item_id}/video")
def quitar_video_inspeccion(
    sesion_id: str,
    item_id: str,
    usuario: User = Depends(require_roles("admin", "bodega")),
    db: Session = Depends(get_db),
) -> dict:
    _sesion_o_404(db, sesion_id)
    item = _item_de_sesion_o_404(db, sesion_id, item_id)
    insp = db.query(ItemInspeccionBodega).filter(ItemInspeccionBodega.item_id == item.id).first()
    if insp is None or not insp.video_url:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Este producto no tiene video")

    url_anterior = insp.video_url
    insp.video_url = None
    insp.actualizado_en = datetime.now(timezone.utc)
    insp.actualizado_por_id = usuario.id
    db.commit()
    borrar_archivos("pedidos", [ruta_desde_url(url_anterior, "pedidos")])

    return {"video_url": None}
