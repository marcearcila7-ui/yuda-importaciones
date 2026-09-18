from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.database import get_db
from app.models.cliente import Cliente
from app.models.item import Item
from app.models.pedido import PedidoGenerado, PedidoGeneradoItem
from app.models.seguimiento import ESTADO_INICIAL, ESTADOS_ENVIO, SeguimientoPedido
from app.models.sesion import Sesion
from app.models.user import User
from app.schemas.bodega import (
    ActualizarTelefonoInput,
    BodegaPedidoDetalle,
    BodegaPedidoResumen,
    GuardarOrdenRealInput,
    OrdenGenerada,
    OrdenGeneradaItem,
)
from app.schemas.portal import PortalItem
from app.schemas.seguimiento import SeguimientoResponse
from app.services.cotizacion_service import _calcular
from app.services.excel_service import generar_csv_pedido, generar_formato_pedido
from app.services.imagen_service import bytes_a_data_uri, descargar_imagenes
from app.services.notificacion_service import avisar_orden_actualizada_bodega
from app.services.pdf_service import html_pedido, render_pdf
from app.services.storage_service import subir_csv, subir_excel, subir_pdf

router = APIRouter(prefix="/bodega", tags=["bodega"])


def _numero(sesion: Sesion) -> str:
    return f"YUDA-{sesion.fecha:%Y%m%d}-{sesion.id[:6].upper()}"


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


@router.get("/pedidos", response_model=list[BodegaPedidoResumen])
def listar_pedidos_bodega(
    estado: str = "proveedor_recibio",
    usuario: User = Depends(require_roles("admin", "bodega")),
    db: Session = Depends(get_db),
) -> list[BodegaPedidoResumen]:
    """Pedidos confirmados en la etapa dada del tracking (por defecto, los que
    ya están con el proveedor y bodega debe revisar y recibir)."""
    if estado not in ESTADOS_ENVIO:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Estado inválido")

    filas = (
        db.query(Sesion, SeguimientoPedido, User)
        .join(SeguimientoPedido, SeguimientoPedido.sesion_id == Sesion.id)
        .outerjoin(User, User.id == Sesion.user_id)
        .filter(
            SeguimientoPedido.estado == estado,
            Sesion.pedido_confirmado_at.isnot(None),
        )
        .order_by(Sesion.pedido_confirmado_at.asc())
        .all()
    )

    resultado: list[BodegaPedidoResumen] = []
    for sesion, seg, vendedora in filas:
        total_items = db.query(Item).filter(Item.sesion_id == sesion.id).count()
        ordenes = db.query(PedidoGenerado).filter(PedidoGenerado.sesion_id == sesion.id).all()
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
            )
        )
    return resultado


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

    # Solo se regenera el archivo si bodega ya contó TODOS los ítems de la
    # orden; a medio llenar, el documento saldría incompleto y confundiría a
    # la vendedora más que ayudarla.
    if all(linea.cantidad_recibida is not None for linea in lineas):
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
        try:
            orden.archivo_real_xlsx_url = subir_excel(excel_bytes, f"{ruta}.xlsx")
            orden.archivo_real_pdf_url = subir_pdf(pdf_bytes, f"{ruta}.pdf")
            orden.archivo_real_csv_url = subir_csv(csv_bytes, f"{ruta}.csv")
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                "No se pudieron guardar los archivos: el almacenamiento no está disponible. "
                "Las cantidades no se guardaron; intenta de nuevo en unos minutos.",
            ) from exc
        orden.revisado_en_bodega_at = datetime.now(timezone.utc)

        avisar_orden_actualizada_bodega(
            db, sesion_id, _numero(sesion), sesion.nombre_cliente, sesion.user_id, orden.supplier
        )

    db.commit()

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
