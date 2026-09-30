from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.database import get_db
from app.models.calendario_pagos import PagoTarea
from app.models.user import User
from app.schemas.calendario_pagos import FeriadoResponse, PagoInput, PagoResponse
from app.services.calendario_pagos_service import (
    actualizar_pago,
    crear_pago,
    eliminar_pago,
    feriados_del_anio,
)

# Solo admin y contadora tienen acceso a este calendario (así lo pidió
# Marcela; ni vendedora ni bodega entran acá).
_ROLES_PAGOS = ("admin", "contadora")

router = APIRouter(prefix="/calendario-pagos", tags=["calendario-pagos"])


def _pago_o_404(db: Session, pago_id: str) -> PagoTarea:
    pago = db.query(PagoTarea).filter(PagoTarea.id == pago_id).first()
    if pago is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pago no encontrado")
    return pago


@router.get("/pagos", response_model=list[PagoResponse])
def listar_pagos(
    desde: date,
    hasta: date,
    usuario: User = Depends(require_roles(*_ROLES_PAGOS)),
    db: Session = Depends(get_db),
) -> list[PagoTarea]:
    """Pagos en un rango de fechas (inclusive), para pintar la vista de mes,
    semana o día que esté usando el frontend."""
    return (
        db.query(PagoTarea)
        .filter(PagoTarea.fecha >= desde, PagoTarea.fecha <= hasta)
        .order_by(PagoTarea.fecha.asc(), PagoTarea.creado_en.asc())
        .all()
    )


@router.post("/pagos", response_model=PagoResponse)
def crear(
    datos: PagoInput,
    usuario: User = Depends(require_roles(*_ROLES_PAGOS)),
    db: Session = Depends(get_db),
) -> PagoTarea:
    return crear_pago(db, datos, usuario)


@router.put("/pagos/{pago_id}", response_model=PagoResponse)
def editar(
    pago_id: str,
    datos: PagoInput,
    usuario: User = Depends(require_roles(*_ROLES_PAGOS)),
    db: Session = Depends(get_db),
) -> PagoTarea:
    """Edición completa de un pago. Arrastrar el pago a otro día en el
    calendario también llama este mismo endpoint, solo que con `fecha`
    distinta y el resto de campos sin cambios -mover un pago es, para el
    backend, una edición más."""
    pago = _pago_o_404(db, pago_id)
    return actualizar_pago(db, pago, datos, usuario)


@router.delete("/pagos/{pago_id}")
def eliminar(
    pago_id: str,
    usuario: User = Depends(require_roles(*_ROLES_PAGOS)),
    db: Session = Depends(get_db),
) -> dict:
    pago = _pago_o_404(db, pago_id)
    eliminar_pago(db, pago)
    return {"ok": True}


@router.get("/feriados", response_model=list[FeriadoResponse])
def feriados(
    anio: int,
    usuario: User = Depends(require_roles(*_ROLES_PAGOS)),
) -> list[dict]:
    return feriados_del_anio(anio)
