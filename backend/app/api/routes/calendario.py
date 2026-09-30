from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.database import get_db
from app.models.calendario import CalendarioNotificacion, CalendarioTarea
from app.models.user import User
from app.schemas.calendario import (
    CalendarioNotificacionResponse,
    FeriadoResponse,
    TareaInput,
    TareaResponse,
)
from app.services.calendario_service import actualizar_tarea, crear_tarea, feriados_del_anio
from app.services.push_service import enviar_push_calendario_en_segundo_plano

# Solo admin, vendedora y bodega tienen acceso a este calendario (así lo
# pidió Marcela; contadora queda afuera a propósito).
_ROLES_CALENDARIO = ("admin", "vendedora", "bodega")

router = APIRouter(prefix="/calendario", tags=["calendario"])


def _tarea_o_404(db: Session, tarea_id: str) -> CalendarioTarea:
    tarea = db.query(CalendarioTarea).filter(CalendarioTarea.id == tarea_id).first()
    if tarea is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarea no encontrada")
    return tarea


@router.get("/tareas", response_model=list[TareaResponse])
def listar_tareas(
    desde: date,
    hasta: date,
    usuario: User = Depends(require_roles(*_ROLES_CALENDARIO)),
    db: Session = Depends(get_db),
) -> list[CalendarioTarea]:
    """Tareas en un rango de fechas (inclusive), para pintar la vista de mes,
    semana o día que esté usando el frontend."""
    return (
        db.query(CalendarioTarea)
        .filter(CalendarioTarea.fecha >= desde, CalendarioTarea.fecha <= hasta)
        .order_by(CalendarioTarea.fecha.asc(), CalendarioTarea.creado_en.asc())
        .all()
    )


@router.post("/tareas", response_model=TareaResponse)
def crear(
    datos: TareaInput,
    background_tasks: BackgroundTasks,
    usuario: User = Depends(require_roles(*_ROLES_CALENDARIO)),
    db: Session = Depends(get_db),
) -> CalendarioTarea:
    tarea, staff_ids, titulo, mensaje = crear_tarea(db, datos, usuario)
    background_tasks.add_task(enviar_push_calendario_en_segundo_plano, staff_ids, titulo, mensaje)
    return tarea


@router.put("/tareas/{tarea_id}", response_model=TareaResponse)
def editar(
    tarea_id: str,
    datos: TareaInput,
    background_tasks: BackgroundTasks,
    usuario: User = Depends(require_roles(*_ROLES_CALENDARIO)),
    db: Session = Depends(get_db),
) -> CalendarioTarea:
    tarea = _tarea_o_404(db, tarea_id)
    tarea, staff_ids, titulo, mensaje = actualizar_tarea(db, tarea, datos, usuario)
    background_tasks.add_task(enviar_push_calendario_en_segundo_plano, staff_ids, titulo, mensaje)
    return tarea


@router.delete("/tareas/{tarea_id}")
def eliminar(
    tarea_id: str,
    usuario: User = Depends(require_roles(*_ROLES_CALENDARIO)),
    db: Session = Depends(get_db),
) -> dict:
    tarea = _tarea_o_404(db, tarea_id)
    db.delete(tarea)
    db.commit()
    return {"ok": True}


@router.get("/feriados", response_model=list[FeriadoResponse])
def feriados(
    anio: int,
    usuario: User = Depends(require_roles(*_ROLES_CALENDARIO)),
) -> list[dict]:
    return feriados_del_anio(anio)


@router.get("/notificaciones", response_model=list[CalendarioNotificacionResponse])
def listar_notificaciones(
    solo_no_leidas: bool = False,
    usuario: User = Depends(require_roles(*_ROLES_CALENDARIO)),
    db: Session = Depends(get_db),
) -> list[CalendarioNotificacion]:
    consulta = db.query(CalendarioNotificacion).filter(CalendarioNotificacion.usuario_id == usuario.id)
    if solo_no_leidas:
        consulta = consulta.filter(CalendarioNotificacion.leida.is_(False))
    return consulta.order_by(CalendarioNotificacion.created_at.desc()).limit(50).all()


@router.post("/notificaciones/leer-todas")
def marcar_todas_leidas(
    usuario: User = Depends(require_roles(*_ROLES_CALENDARIO)),
    db: Session = Depends(get_db),
) -> dict:
    db.query(CalendarioNotificacion).filter(
        CalendarioNotificacion.usuario_id == usuario.id, CalendarioNotificacion.leida.is_(False)
    ).update({CalendarioNotificacion.leida: True})
    db.commit()
    return {"ok": True}
