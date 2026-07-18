from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.rate_limit import esta_bloqueado, ip_del_request, limpiar, registrar_fallo

from app.api.dependencies import get_current_cliente
from app.core.security import create_access_token, verify_password
from app.database import get_db
from app.models.cliente import Cliente
from app.models.item import Item
from app.models.seguimiento import ESTADO_INICIAL, SeguimientoPedido
from app.models.sesion import (
    PEDIDO_CONFIRMADO,
    PEDIDO_POR_CONFIRMAR,
    PEDIDO_RECIBIDO,
    Sesion,
)
from app.schemas.cliente import ClienteLogin, ClientePublic, ClienteTokenResponse
from app.schemas.cotizacion import CotizacionRequest
from app.services.notificacion_service import (
    avisar_pedido_cliente,
    avisar_pedido_confirmado,
)
from app.schemas.portal import (
    PortalCotizacionDetalle,
    PortalCotizacionResumen,
    PortalItem,
    PortalPedidoInput,
)
from app.schemas.seguimiento import SeguimientoResponse
from app.services.cotizacion_service import (
    _calcular,
    generar_cotizacion_excel,
    generar_cotizacion_pdf,
)

router = APIRouter(prefix="/portal", tags=["portal"])


def _numero(sesion: Sesion) -> str:
    return f"YUDA-{sesion.fecha:%Y%m%d}-{sesion.id[:6].upper()}"


def _sesion_del_cliente(db: Session, sesion_id: str, cliente: Cliente) -> Sesion:
    """Devuelve la cotización si pertenece al cliente y fue enviada; si no, 404"""
    sesion = (
        db.query(Sesion)
        .filter(
            Sesion.id == sesion_id,
            Sesion.cliente_id == cliente.id,
            Sesion.enviada_cliente.is_(True),
        )
        .first()
    )
    if sesion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cotización no encontrada")
    return sesion


@router.post("/login", response_model=ClienteTokenResponse)
def login_cliente(
    datos: ClienteLogin, request: Request, db: Session = Depends(get_db)
) -> ClienteTokenResponse:
    """Login del portal de clientes"""
    email = datos.email.strip().lower()
    clave_email = f"portal:email:{email}"
    clave_ip = f"portal:ip:{ip_del_request(request)}"
    if esta_bloqueado(clave_email, 5, 15 * 60) or esta_bloqueado(clave_ip, 20, 15 * 60):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Demasiados intentos fallidos. Espera unos minutos e intenta de nuevo.",
        )
    cliente = db.query(Cliente).filter(Cliente.email == email).first()

    if cliente is None or not verify_password(datos.password, cliente.hashed_password):
        registrar_fallo(clave_email, 15 * 60)
        registrar_fallo(clave_ip, 15 * 60)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales incorrectas")
    if not cliente.activo:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cuenta inactiva")

    limpiar(clave_email)
    token = create_access_token(
        {"sub": cliente.id, "tipo": "cliente", "tv": cliente.token_version}
    )
    return ClienteTokenResponse(
        access_token=token,
        cliente=ClientePublic.model_validate(cliente),
    )


@router.get("/me", response_model=ClientePublic)
def me_cliente(cliente: Cliente = Depends(get_current_cliente)) -> Cliente:
    return cliente


@router.get("/cotizaciones", response_model=list[PortalCotizacionResumen])
def mis_cotizaciones(
    cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db),
) -> list[PortalCotizacionResumen]:
    """Cotizaciones que la vendedora envió a este cliente"""
    sesiones = (
        db.query(Sesion)
        .filter(Sesion.cliente_id == cliente.id, Sesion.enviada_cliente.is_(True))
        .order_by(Sesion.created_at.desc())
        .all()
    )

    resumenes: list[PortalCotizacionResumen] = []
    for s in sesiones:
        items = db.query(Item).filter(Item.sesion_id == s.id).all()
        total_usd = sum(_calcular(i, s.tipo_cambio_usd)["total_usd"] for i in items)
        seg = db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == s.id).first()
        resumenes.append(
            PortalCotizacionResumen(
                sesion_id=s.id,
                numero=_numero(s),
                nombre_cliente=s.nombre_cliente,
                fecha=s.fecha,
                total_items=len(items),
                total_usd=round(total_usd, 2),
                estado=seg.estado if seg else ESTADO_INICIAL,
                actualizado=seg.updated_at if seg else None,
            )
        )
    return resumenes


@router.get("/cotizaciones/{sesion_id}", response_model=PortalCotizacionDetalle)
def detalle_cotizacion(
    sesion_id: str,
    cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db),
) -> PortalCotizacionDetalle:
    """Detalle de una cotización: productos (vista cliente) + seguimiento"""
    sesion = _sesion_del_cliente(db, sesion_id, cliente)
    items = (
        db.query(Item).filter(Item.sesion_id == sesion_id).order_by(Item.orden.asc()).all()
    )

    portal_items: list[PortalItem] = []
    total_usd = 0.0
    total_cbm = 0.0
    for i in items:
        calc = _calcular(i, sesion.tipo_cambio_usd)
        total_usd += calc["total_usd"]
        total_cbm += calc["t_cbm"]
        portal_items.append(
            PortalItem(
                item_id=i.id,
                foto_url=i.foto_url,
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

    seg = db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == sesion_id).first()
    seguimiento = (
        SeguimientoResponse.model_validate(seg)
        if seg
        else SeguimientoResponse(estado=ESTADO_INICIAL)
    )

    return PortalCotizacionDetalle(
        sesion_id=sesion.id,
        numero=_numero(sesion),
        nombre_cliente=sesion.nombre_cliente,
        fecha=sesion.fecha,
        items=portal_items,
        total_usd=round(total_usd, 2),
        total_cbm=round(total_cbm, 6),
        seguimiento=seguimiento,
        notas_cliente=sesion.notas_cliente,
        pedido_recibido=sesion.pedido_recibido_at is not None,
        pedido_estado=sesion.pedido_estado,
        pedido_confirmado=sesion.pedido_confirmado_at is not None,
    )


@router.put("/cotizaciones/{sesion_id}/pedido")
def enviar_pedido(
    sesion_id: str,
    datos: PortalPedidoInput,
    cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db),
) -> dict:
    """El cliente envía, desde su portal, las cajas que desea de cada producto
    (para el pedido al proveedor) y sus notas. Solo puede tocar su propia
    cotización enviada. Editable las veces que quiera."""
    sesion = _sesion_del_cliente(db, sesion_id, cliente)
    items = {i.id: i for i in db.query(Item).filter(Item.sesion_id == sesion_id).all()}
    for linea in datos.items:
        it = items.get(linea.item_id)
        if it is None:
            continue  # ignora ítems que no son de esta cotización
        it.cantidad_solicitada = linea.cantidad if linea.cantidad and linea.cantidad > 0 else None
    sesion.notas_cliente = (datos.notas or "").strip() or None
    sesion.pedido_recibido_at = datetime.now(timezone.utc)
    # El cliente propone (o re-propone) cantidades → vuelve a "recibido" para que
    # la vendedora las revise. Se limpia cualquier confirmación previa.
    sesion.pedido_estado = PEDIDO_RECIBIDO
    sesion.pedido_confirmado_at = None
    # Avisa a la vendedora dueña y a Marcela que el cliente ya envió su pedido.
    avisar_pedido_cliente(db, sesion.id, _numero(sesion), sesion.nombre_cliente, sesion.user_id)
    db.commit()
    return {"detail": "Pedido recibido"}


@router.post("/cotizaciones/{sesion_id}/confirmar")
def confirmar_pedido(
    sesion_id: str,
    cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db),
) -> dict:
    """El cliente confirma las cantidades finales que le envió la vendedora. Solo
    se puede confirmar cuando el pedido está "por confirmar". Al confirmar, la
    vendedora ya puede generar el pedido al proveedor."""
    sesion = _sesion_del_cliente(db, sesion_id, cliente)
    if sesion.pedido_estado != PEDIDO_POR_CONFIRMAR:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este pedido no está pendiente de tu confirmación.",
        )
    sesion.pedido_estado = PEDIDO_CONFIRMADO
    sesion.pedido_confirmado_at = datetime.now(timezone.utc)
    avisar_pedido_confirmado(db, sesion.id, _numero(sesion), sesion.nombre_cliente, sesion.user_id)
    db.commit()
    return {"detail": "Pedido confirmado"}


@router.post("/cotizaciones/{sesion_id}/cotizacion-excel")
def descargar_cotizacion_excel(
    sesion_id: str,
    datos: CotizacionRequest,
    cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db),
) -> Response:
    """Descarga el Excel de la cotización (vista cliente)"""
    sesion = _sesion_del_cliente(db, sesion_id, cliente)
    items = (
        db.query(Item).filter(Item.sesion_id == sesion_id).order_by(Item.orden.asc()).all()
    )
    contenido = generar_cotizacion_excel(items, sesion, datos.idioma, sesion.tipo_cambio_usd)
    fecha = datetime.now().strftime("%Y%m%d")
    nombre = f"{fecha}_Cotizacion_{datos.idioma}.xlsx"
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.post("/cotizaciones/{sesion_id}/cotizacion-pdf")
def descargar_cotizacion_pdf(
    sesion_id: str,
    datos: CotizacionRequest,
    cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db),
) -> Response:
    """Descarga el PDF de la cotización (vista cliente)"""
    sesion = _sesion_del_cliente(db, sesion_id, cliente)
    items = (
        db.query(Item).filter(Item.sesion_id == sesion_id).order_by(Item.orden.asc()).all()
    )
    contenido = generar_cotizacion_pdf(items, sesion, datos.idioma, sesion.tipo_cambio_usd)
    fecha = datetime.now().strftime("%Y%m%d")
    nombre = f"{fecha}_Cotizacion_{datos.idioma}.pdf"
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
