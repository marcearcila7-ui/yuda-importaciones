from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.database import get_db
from app.models.push_subscription import PushSubscription
from app.models.user import User
from app.schemas.push import PushSubscriptionInput, PushUnsubscribeInput, VapidPublicKeyResponse

# Se monta en main.py bajo /api/v1
router = APIRouter(prefix="/push", tags=["push"])


@router.get("/vapid-public-key", response_model=VapidPublicKeyResponse)
def vapid_public_key() -> VapidPublicKeyResponse:
    """La llave pública VAPID, para que el navegador la use al suscribirse.
    Se sirve desde acá (no queda fija en el build del frontend) para poder
    rotarla algún día sin tener que republicar la app."""
    return VapidPublicKeyResponse(public_key=settings.VAPID_PUBLIC_KEY)


@router.post("/suscribir")
def suscribir(
    datos: PushSubscriptionInput,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Guarda (o actualiza) la suscripción push de este navegador para el
    usuario autenticado. El mismo endpoint puede repetirse en el mismo
    navegador (el service worker vuelve a suscribirse) sin duplicar filas."""
    existente = db.query(PushSubscription).filter(PushSubscription.endpoint == datos.endpoint).first()
    if existente:
        existente.usuario_id = usuario.id
        existente.p256dh = datos.p256dh
        existente.auth = datos.auth
    else:
        db.add(
            PushSubscription(
                usuario_id=usuario.id,
                endpoint=datos.endpoint,
                p256dh=datos.p256dh,
                auth=datos.auth,
            )
        )
    db.commit()
    return {"ok": True}


@router.post("/desuscribir")
def desuscribir(
    datos: PushUnsubscribeInput,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """El usuario apagó las notificaciones en este navegador (o cerró
    sesión): borra esa suscripción puntual."""
    db.query(PushSubscription).filter(
        PushSubscription.endpoint == datos.endpoint, PushSubscription.usuario_id == usuario.id
    ).delete()
    db.commit()
    return {"ok": True}
