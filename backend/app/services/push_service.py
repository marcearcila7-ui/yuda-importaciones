import base64
import json
import logging

from py_vapid import Vapid01
from pywebpush import WebPushException, webpush
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)


def _vapid() -> Vapid01 | None:
    """Reconstruye la llave privada VAPID a partir del PEM en base64 guardado
    en la variable de entorno (así sobrevive como texto de una sola línea sin
    que los saltos de línea del PEM se corrompan)."""
    if not settings.VAPID_PRIVATE_KEY_B64:
        return None
    pem = base64.b64decode(settings.VAPID_PRIVATE_KEY_B64)
    return Vapid01.from_pem(pem)


def enviar_push(db: Session, usuario_id: str, titulo: str, mensaje: str, sesion_id: str | None = None) -> None:
    """Manda una notificación push a todos los navegadores suscritos de este
    usuario. Es "mejor esfuerzo": si VAPID no está configurado, o el envío
    falla, no interrumpe el flujo que la llamó -la notificación ya quedó
    guardada en la campanita de todas formas. Si el navegador ya no existe
    (respondió 404/410), se borra esa suscripción."""
    vv = _vapid()
    if vv is None:
        return
    subs = db.query(PushSubscription).filter(PushSubscription.usuario_id == usuario_id).all()
    if not subs:
        return

    payload = json.dumps({"titulo": titulo, "mensaje": mensaje, "sesion_id": sesion_id})
    vencidas: list[str] = []
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=vv,
                vapid_claims={"sub": settings.VAPID_CLAIMS_EMAIL},
            )
        except WebPushException as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status in (404, 410):
                vencidas.append(sub.id)
            else:
                logger.warning("Push falló para usuario %s: %s", usuario_id, exc)
        except Exception as exc:  # nunca debe tumbar el flujo que llamó a esto
            logger.warning("Push falló para usuario %s: %s", usuario_id, exc)

    if vencidas:
        # No se hace commit acá: se deja que el commit del flujo que llamó a
        # esto (el que crea la notificación) persista también esta limpieza.
        db.query(PushSubscription).filter(PushSubscription.id.in_(vencidas)).delete(synchronize_session=False)
