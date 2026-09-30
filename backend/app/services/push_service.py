import base64
import json
import logging

from py_vapid import Vapid01
from pywebpush import WebPushException, webpush
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import SessionLocal
from app.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)

# Límite duro por envío: sin esto, un proveedor de push lento o caído puede
# dejar colgado el hilo (y la conexión a la base de datos que tiene abierta)
# indefinidamente. Con varios usuarios creando/editando tareas del calendario
# a la vez -cada uno avisándole a todo el staff- este límite es lo que evita
# que unos pocos envíos lentos frenen a todos los demás.
_TIMEOUT_PUSH = 5


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
                timeout=_TIMEOUT_PUSH,
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


def enviar_push_a_varios(db: Session, usuario_ids: list[str], titulo: str, mensaje: str) -> None:
    """Igual que enviar_push, pero para varios usuarios a la vez (ej. avisar
    a todo el staff de una tarea nueva del calendario): una sola consulta de
    suscripciones en vez de una por usuario."""
    if not usuario_ids:
        return
    vv = _vapid()
    if vv is None:
        return
    subs = db.query(PushSubscription).filter(PushSubscription.usuario_id.in_(usuario_ids)).all()
    if not subs:
        return

    payload = json.dumps({"titulo": titulo, "mensaje": mensaje, "sesion_id": None})
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
                timeout=_TIMEOUT_PUSH,
            )
        except WebPushException as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status in (404, 410):
                vencidas.append(sub.id)
            else:
                logger.warning("Push falló para usuario %s: %s", sub.usuario_id, exc)
        except Exception as exc:  # nunca debe tumbar el flujo que llamó a esto
            logger.warning("Push falló para usuario %s: %s", sub.usuario_id, exc)

    if vencidas:
        db.query(PushSubscription).filter(PushSubscription.id.in_(vencidas)).delete(synchronize_session=False)


def enviar_push_calendario_en_segundo_plano(usuario_ids: list[str], titulo: str, mensaje: str) -> None:
    """Envoltorio para usar con BackgroundTasks de FastAPI: crea su propia
    sesión de base de datos (la del request ya se cerró cuando esto corre) y
    nunca bloquea la respuesta al usuario. Así, si 50 personas crean/editan
    tareas del calendario al mismo tiempo -cada una avisándole a todo el
    staff- el envío de los push no alarga ni una sola de esas respuestas."""
    db = SessionLocal()
    try:
        enviar_push_a_varios(db, usuario_ids, titulo, mensaje)
        db.commit()
    except Exception as exc:  # nunca debe tumbar el proceso en background
        logger.warning("Envío de push en segundo plano falló: %s", exc)
    finally:
        db.close()
