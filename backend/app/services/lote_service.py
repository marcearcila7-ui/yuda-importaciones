import asyncio
import logging

import httpx

from app.core.config import settings
from app.database import SessionLocal
from app.models.lote import LoteItem, LoteOCR
from app.services.ocr_service import es_error_sistema, extraer_datos_etiqueta

logger = logging.getLogger(__name__)

# Fotos en paralelo dentro de un mismo lote (acota memoria/descargas por job).
# El tope GLOBAL de llamadas reales a Anthropic vive en ocr_service (semáforo global),
# así que aunque corran muchos lotes a la vez, el OCR nunca se dispara sin control.
CONCURRENCIA = settings.OCR_CONCURRENCIA_LOTE

# Si las primeras fotos fallan por un problema del sistema (API caída, sin crédito),
# van a fallar TODAS: se corta el lote ahí en vez de quemar 100 fotos. El 15-ago-2026
# una vendedora reintentó tres veces —268 fotos— porque la app no le dijo que el
# problema era nuestro.
FALLOS_SEGUIDOS_PARA_CORTAR = 3


def _media_type(url: str) -> str:
    u = url.lower()
    if u.endswith(".png"):
        return "image/png"
    if u.endswith(".webp"):
        return "image/webp"
    return "image/jpeg"


async def ocr_de_url(foto_url: str) -> tuple[dict | None, str]:
    """Descarga una foto y le corre el OCR. Devuelve (datos, estado 'ok'|'error').

    'ok' significa que el modelo respondió (aunque la marque ilegible; eso se
    resuelve luego con los datos). 'error' es un fallo duro (no se pudo descargar
    o procesar la imagen)."""
    try:
        async with httpx.AsyncClient() as cli:
            resp = await cli.get(foto_url, timeout=20)
        if resp.status_code == 200:
            datos = await extraer_datos_etiqueta(resp.content, _media_type(foto_url))
            return datos, "ok"
    except Exception:
        logger.exception("Error reanalizando foto %s", foto_url)
    return None, "error"


async def ocr_de_bytes(imagen_bytes: bytes, media_type: str) -> tuple[dict | None, str]:
    """Corre el OCR sobre una imagen ya en memoria. Devuelve (datos, estado)."""
    try:
        datos = await extraer_datos_etiqueta(imagen_bytes, media_type)
        return datos, "ok"
    except Exception:
        logger.exception("Error analizando imagen subida al lote")
        return None, "error"


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

    # Estado compartido para poder cortar el lote si el sistema esta fallando.
    cortado = {"activo": False, "fallos": 0}

    async def procesar_uno(item_id: str, foto_url: str) -> None:
        async with sem:
            if cortado["activo"]:
                return          # el lote se corto: esta foto queda pendiente para reintentar
            datos = None
            estado = "error"
            try:
                async with httpx.AsyncClient() as cli:
                    resp = await cli.get(foto_url, timeout=20)
                if resp.status_code == 200:
                    datos = await extraer_datos_etiqueta(resp.content, _media_type(foto_url))
                    # Un fallo del sistema NO es una foto "procesada": marcarla 'ok'
                    # hacia la vendedora como "no legible" es echarle la culpa a ella.
                    estado = "error" if es_error_sistema(datos) else "ok"
            except Exception:
                logger.exception("Error procesando ítem de lote %s", item_id)

            if estado == "error" and es_error_sistema(datos):
                cortado["fallos"] += 1
                if cortado["fallos"] >= FALLOS_SEGUIDOS_PARA_CORTAR:
                    cortado["activo"] = True
                    logger.error(
                        "Lote %s cortado: %d fotos seguidas fallaron por error del sistema",
                        lote_id, cortado["fallos"],
                    )
            elif estado == "ok":
                cortado["fallos"] = 0
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

    # 2. Cerrar el lote. Si se corto por fallos del sistema, o si NINGUNA foto salio
    # bien, el lote NO esta "completado": queda en error para que la app lo diga y
    # ofrezca reintentar sin volver a fotografiar nada (las fotos ya estan guardadas).
    d = SessionLocal()
    try:
        lote = d.query(LoteOCR).filter(LoteOCR.id == lote_id).first()
        if lote:
            hechas = (
                d.query(LoteItem)
                .filter(LoteItem.lote_id == lote_id, LoteItem.estado == "ok")
                .count()
            )
            lote.estado = "error" if (cortado["activo"] or hechas == 0) else "completado"
            d.commit()
    finally:
        d.close()
