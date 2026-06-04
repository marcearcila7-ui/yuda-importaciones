from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_cliente
from app.core.security import create_access_token, verify_password
from app.database import get_db
from app.models.cliente import Cliente
from app.models.item import Item
from app.models.seguimiento import ESTADO_INICIAL, SeguimientoPedido
from app.models.sesion import Sesion
from app.schemas.cliente import ClienteLogin, ClientePublic, ClienteTokenResponse
from app.schemas.cotizacion import CotizacionRequest
from app.schemas.portal import (
    PortalCotizacionDetalle,
    PortalCotizacionResumen,
    PortalItem,
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
def login_cliente(datos: ClienteLogin, db: Session = Depends(get_db)) -> ClienteTokenResponse:
    """Login del portal de clientes"""
    email = datos.email.strip().lower()
    cliente = db.query(Cliente).filter(Cliente.email == email).first()

    if cliente is None or not verify_password(datos.password, cliente.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales incorrectas")
    if not cliente.activo:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cuenta inactiva")

    token = create_access_token({"sub": cliente.id, "tipo": "cliente"})
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
    )


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
