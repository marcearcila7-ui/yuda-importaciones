"""Worker de la cola de OCR (proceso aparte del web).

Arranque:  python -m app.worker

Toma lotes 'encolado' de la base, los marca 'procesando' y corre el OCR.
La cola vive en Postgres (tablas lotes_ocr / lote_items), así que sobrevive
reinicios: si el worker se cae, al volver retoma lo pendiente. El proceso web
deja de hacer OCR y queda siempre responsivo.

Requiere USE_WORKER=true en el servicio web (para que encole en vez de procesar
en segundo plano). El worker procesa la cola independientemente del flag.
"""
import asyncio
import logging

from app.core.config import settings
from app.core.logging_setup import configurar_logging
from app.database import SessionLocal
from app.models.lote import LoteOCR
from app.services.lote_service import procesar_lote

logger = logging.getLogger("worker")


def _requeue_huerfanos() -> int:
    """Re-encola lotes que quedaron 'procesando' por un corte previo.

    Asume un único worker. Para correr varios workers a la vez haría falta un
    heartbeat por lote; con uno solo, un 'procesando' al arrancar = corte previo.
    """
    db = SessionLocal()
    try:
        n = (
            db.query(LoteOCR)
            .filter(LoteOCR.estado == "procesando")
            .update({LoteOCR.estado: "encolado"})
        )
        db.commit()
        return n
    finally:
        db.close()


def _reclamar_lote() -> str | None:
    """Toma el lote encolado más antiguo de forma atómica (FOR UPDATE SKIP LOCKED)."""
    db = SessionLocal()
    try:
        lote = (
            db.query(LoteOCR)
            .filter(LoteOCR.estado == "encolado")
            .order_by(LoteOCR.created_at.asc())
            .with_for_update(skip_locked=True)
            .first()
        )
        if lote is None:
            return None
        lote.estado = "procesando"
        db.commit()
        return lote.id
    finally:
        db.close()


async def main() -> None:
    configurar_logging()
    logger.info("iniciado · poll=%ss", settings.WORKER_POLL_SECONDS)
    try:
        requeued = _requeue_huerfanos()
        if requeued:
            logger.info("re-encolados %s lote(s) huérfanos de un corte previo", requeued)
    except Exception:  # noqa: BLE001
        logger.exception("no se pudo re-encolar huérfanos")

    while True:
        try:
            lote_id = _reclamar_lote()
        except Exception:  # noqa: BLE001
            logger.exception("error reclamando lote")
            lote_id = None

        if lote_id is None:
            await asyncio.sleep(settings.WORKER_POLL_SECONDS)
            continue

        logger.info("procesando lote %s", lote_id)
        try:
            await procesar_lote(lote_id)
            logger.info("lote %s completado", lote_id)
        except Exception:  # noqa: BLE001
            logger.exception("error procesando lote %s", lote_id)


if __name__ == "__main__":
    asyncio.run(main())
