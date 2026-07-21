from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.database import get_db
from app.models.tienda import PedidoTienda
from app.models.user import RolUsuario, User
from app.schemas.tienda import (
    ComisionesReporte,
    EmpleadaResumen,
    PedidoTiendaCreate,
    PedidoTiendaResponse,
    PedidoTiendaUpdate,
)
from app.services.tienda_service import (
    construir_response,
    reporte_comisiones,
    revisar_alertas_pago_70,
)

# Se monta en main.py bajo /api/v1. Gestión: admin y contadora.
router = APIRouter(tags=["tiendas"])


@router.get("/tiendas/empleadas", response_model=list[EmpleadaResumen])
def listar_empleadas(
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> list[User]:
    """Empleadas (vendedoras y admin) activas, para asociar a pedidos / ranking."""
    return (
        db.query(User)
        .filter(
            User.activo.is_(True),
            User.rol.in_([RolUsuario.vendedora, RolUsuario.admin]),
        )
        .order_by(User.nombre.asc())
        .all()
    )


def _obtener_pedido(db: Session, pedido_id: str) -> PedidoTienda:
    pedido = db.query(PedidoTienda).filter(PedidoTienda.id == pedido_id).first()
    if pedido is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido a tienda no encontrado")
    return pedido


@router.get("/tiendas/pedidos", response_model=list[PedidoTiendaResponse])
def listar_pedidos_tienda(
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Lista los pedidos a tiendas (del más reciente al más antiguo).

    De paso revisa y genera los avisos del 70% por vencer (aparecen en la campana).
    """
    revisar_alertas_pago_70(db)
    hoy = date.today()
    pedidos = db.query(PedidoTienda).order_by(PedidoTienda.created_at.desc()).all()
    return [construir_response(p, db, hoy) for p in pedidos]


@router.get("/tiendas/comisiones", response_model=ComisionesReporte)
def comisiones_tienda(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> dict:
    """Comisiones recibidas de tiendas en el período (mes/trimestre/año) + total."""
    return reporte_comisiones(db, desde, hasta)


@router.get("/tiendas/pedidos/{pedido_id}", response_model=PedidoTiendaResponse)
def obtener_pedido_tienda(
    pedido_id: str,
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> dict:
    return construir_response(_obtener_pedido(db, pedido_id), db)


@router.post(
    "/tiendas/pedidos",
    response_model=PedidoTiendaResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_pedido_tienda(
    datos: PedidoTiendaCreate,
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> dict:
    pedido = PedidoTienda(
        nombre_tienda=datos.nombre_tienda.strip(),
        fecha_pedido=datos.fecha_pedido,
        monto_total=datos.monto_total,
        fecha_pago_30=datos.fecha_pago_30,
        fecha_estimada_entrega=datos.fecha_estimada_entrega,
        fecha_real_entrega=datos.fecha_real_entrega,
        fecha_estimada_pago_70=datos.fecha_estimada_pago_70,
        fecha_pago_70=datos.fecha_pago_70,
        pct_comision_tienda=datos.pct_comision_tienda,
        fecha_comision=datos.fecha_comision,
        empleada_id=datos.empleada_id,
        notas=datos.notas,
    )
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return construir_response(pedido, db)


@router.patch("/tiendas/pedidos/{pedido_id}", response_model=PedidoTiendaResponse)
def actualizar_pedido_tienda(
    pedido_id: str,
    datos: PedidoTiendaUpdate,
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> dict:
    pedido = _obtener_pedido(db, pedido_id)
    cambios = datos.model_dump(exclude_unset=True)
    if "nombre_tienda" in cambios and cambios["nombre_tienda"] is not None:
        cambios["nombre_tienda"] = cambios["nombre_tienda"].strip()
    for campo, valor in cambios.items():
        setattr(pedido, campo, valor)
    db.commit()
    db.refresh(pedido)
    return construir_response(pedido, db)


@router.delete("/tiendas/pedidos/{pedido_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_pedido_tienda(
    pedido_id: str,
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> None:
    pedido = _obtener_pedido(db, pedido_id)
    db.delete(pedido)
    db.commit()
