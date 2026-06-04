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

from app.core.config import settings
from app.database import SessionLocal
from app.models.lote import LoteOCR
from app.services.lote_service import procesar_lote


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
    print(f"[worker] iniciado · poll={settings.WORKER_POLL_SECONDS}s")
    try:
        requeued = _requeue_huerfanos()
        if requeued:
            print(f"[worker] re-encolados {requeued} lote(s) huérfanos de un corte previo")
    except Exception as e:  # noqa: BLE001
        print(f"[worker] no se pudo re-encolar huérfanos: {e}")

    while True:
        try:
            lote_id = _reclamar_lote()
        except Exception as e:  # noqa: BLE001
            print(f"[worker] error reclamando lote: {e}")
            lote_id = None

        if lote_id is None:
            await asyncio.sleep(settings.WORKER_POLL_SECONDS)
            continue

        print(f"[worker] procesando lote {lote_id}")
        try:
            await procesar_lote(lote_id)
            print(f"[worker] lote {lote_id} completado")
        except Exception as e:  # noqa: BLE001
            print(f"[worker] error procesando lote {lote_id}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
