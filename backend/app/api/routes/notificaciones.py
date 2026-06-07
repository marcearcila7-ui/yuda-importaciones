from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.notificacion import Notificacion
from app.models.user import User
from app.schemas.notificacion import NotificacionResponse

# Se monta en main.py bajo /api/v1
router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])


@router.get("", response_model=list[NotificacionResponse])
def listar_notificaciones(
    solo_no_leidas: bool = False,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Notificacion]:
    """Avisos del usuario autenticado, los más recientes primero"""
    consulta = db.query(Notificacion).filter(Notificacion.usuario_id == usuario.id)
    if solo_no_leidas:
        consulta = consulta.filter(Notificacion.leida.is_(False))
    return consulta.order_by(Notificacion.created_at.desc()).limit(50).all()


@router.post("/{notificacion_id}/leer", response_model=NotificacionResponse)
def marcar_leida(
    notificacion_id: str,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Notificacion:
    """Marca un aviso como leído"""
    notif = (
        db.query(Notificacion)
        .filter(Notificacion.id == notificacion_id, Notificacion.usuario_id == usuario.id)
        .first()
    )
    if notif is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aviso no encontrado")
    notif.leida = True
    db.commit()
    db.refresh(notif)
    return notif


@router.post("/leer-todas")
def marcar_todas_leidas(
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Marca todos los avisos del usuario como leídos"""
    db.query(Notificacion).filter(
        Notificacion.usuario_id == usuario.id, Notificacion.leida.is_(False)
    ).update({Notificacion.leida: True})
    db.commit()
    return {"ok": True}
