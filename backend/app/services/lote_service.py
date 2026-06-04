import asyncio

import httpx

from app.database import SessionLocal
from app.models.lote import LoteItem, LoteOCR
from app.services.ocr_service import extraer_datos_etiqueta

# Cuántas fotos del lote se leen en paralelo
CONCURRENCIA = 4


def _media_type(url: str) -> str:
    u = url.lower()
    if u.endswith(".png"):
        return "image/png"
    if u.endswith(".webp"):
        return "image/webp"
    return "image/jpeg"


async def procesar_lote(lote_id: str) -> None:
    """Procesa en segundo plano todas las fotos pendientes de un lote.

    Corre fuera del request: la vendedora puede cerrar la app y al volver
    consulta el estado. Nunca lanza excepción hacia afuera.
    """
    # 1. Tomar los ítems pendientes
    db = SessionLocal()
    try:
        items = (
            db.query(LoteItem)
            .filter(LoteItem.lote_id == lote_id, LoteItem.estado == "pendiente")
            .all()
        )
        trabajos = [(i.id, i.foto_url) for i in items]
    finally:
        db.close()

    sem = asyncio.Semaphore(CONCURRENCIA)

    async def procesar_uno(item_id: str, foto_url: str) -> None:
        async with sem:
            datos = None
            estado = "error"
            try:
                async with httpx.AsyncClient() as cli:
                    resp = await cli.get(foto_url, timeout=20)
                if resp.status_code == 200:
                    datos = await extraer_datos_etiqueta(resp.content, _media_type(foto_url))
                    estado = "ok"
            except Exception as e:
                print(f"Error procesando ítem de lote {item_id}: {e}")
            # Actualizar en una sesión propia (cada tarea con la suya)
            d = SessionLocal()
            try:
                it = d.query(LoteItem).filter(LoteItem.id == item_id).first()
                if it:
                    it.datos = datos
                    it.estado = estado
                    d.commit()
            finally:
                d.close()

    await asyncio.gather(*[procesar_uno(i, u) for i, u in trabajos])

    # 2. Marcar el lote como completado
    d = SessionLocal()
    try:
        lote = d.query(LoteOCR).filter(LoteOCR.id == lote_id).first()
        if lote:
            lote.estado = "completado"
            d.commit()
    finally:
        d.close()
