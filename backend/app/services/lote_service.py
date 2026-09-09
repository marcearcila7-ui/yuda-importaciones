import asyncio
import logging

import httpx

from app.core.config import settings
from app.database import SessionLocal
from app.models.lote import LoteItem, LoteOCR
from app.models.sesion import Sesion
from app.services.ocr_service import es_error_sistema, extraer_datos_etiqueta
from app.services.recorte_service import recortar_producto, recuadro_fuera_del_cartel
from app.services.storage_service import subir_foto

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


async def adjuntar_recorte(datos: dict | None, imagen_bytes: bytes) -> None:
    """Recorta el producto y guarda el recorte en `datos["foto_recorte_url"]`.

    Es la foto que despues va a los documentos del cliente y del proveedor. Si el
    modelo no marco un recuadro usable, o el recorte o la subida fallan, se deja
    en None y los documentos usan la foto completa como siempre: nunca se pierde
    el producto por no haber podido recortarlo.
    """
    if not datos:
        return
    recuadro = datos.get("recuadro_producto")
    if not recuadro:
        # Plan B: si ubico el cartel que leyo pero no marco el producto, se recorta
        # lo que queda al sacar el cartel. Es lo que haria la vendedora a mano.
        cartel = datos.get("recuadro_cartel")
        recuadro = recuadro_fuera_del_cartel(cartel) if cartel else None
        if recuadro:
            logger.info("Recorte deducido del cartel: %s", recuadro)
    giro = datos.get("giro_necesario") or 0
    if not recuadro and not giro:
        logger.info("Sin recuadro ni giro: la foto va entera a los documentos")
        return
    recorte = recortar_producto(imagen_bytes, recuadro, giro)
    if recorte is None:
        return
    try:
        import uuid

        loop = asyncio.get_event_loop()
        nombre = f"{uuid.uuid4()}.jpg"
        url = await loop.run_in_executor(
            None, lambda: subir_foto(recorte, nombre, "image/jpeg")
        )
        datos["foto_recorte_url"] = url
    except Exception:
        logger.exception("No se pudo guardar el recorte del producto")


def _media_type(url: str) -> str:
    u = url.lower()
    if u.endswith(".png"):
        return "image/png"
    if u.endswith(".webp"):
        return "image/webp"
    return "image/jpeg"


async def ocr_de_url(foto_url: str, tipo_cotizacion: str = "productos") -> tuple[dict | None, str]:
    """Descarga una foto y le corre el OCR. Devuelve (datos, estado 'ok'|'error').

    'ok' significa que el modelo respondió (aunque la marque ilegible; eso se
    resuelve luego con los datos). 'error' es un fallo duro (no se pudo descargar
    o procesar la imagen)."""
    try:
        async with httpx.AsyncClient() as cli:
            resp = await cli.get(foto_url, timeout=20)
        if resp.status_code == 200:
            datos = await extraer_datos_etiqueta(resp.content, _media_type(foto_url), tipo_cotizacion)
            await adjuntar_recorte(datos, resp.content)
            return datos, "ok"
    except Exception:
        logger.exception("Error reanalizando foto %s", foto_url)
    return None, "error"


async def ocr_de_bytes(
    imagen_bytes: bytes, media_type: str, tipo_cotizacion: str = "productos"
) -> tuple[dict | None, str]:
    """Corre el OCR sobre una imagen ya en memoria. Devuelve (datos, estado)."""
    try:
        datos = await extraer_datos_etiqueta(imagen_bytes, media_type, tipo_cotizacion)
        await adjuntar_recorte(datos, imagen_bytes)
        return datos, "ok"
    except Exception:
        logger.exception("Error analizando imagen subida al lote")
        return None, "error"


async def procesar_lote(lote_id: str) -> None:
    """Procesa en segundo plano todas las fotos pendientes de un lote.

    Corre fuera del request: la vendedora puede cerrar la app y al volver
    consulta el estado. Nunca lanza excepción hacia afuera.
    """
    # 1. Tomar los ítems pendientes y el tipo de cotización de la sesión (una
    # sola vez: le dice al OCR si tiene que leer también los campos de bolso).
    db = SessionLocal()
    try:
        items = (
            db.query(LoteItem)
            .filter(LoteItem.lote_id == lote_id, LoteItem.estado == "pendiente")
            .all()
        )
        trabajos = [(i.id, i.foto_url) for i in items]
        lote = db.query(LoteOCR).filter(LoteOCR.id == lote_id).first()
        sesion = db.query(Sesion).filter(Sesion.id == lote.sesion_id).first() if lote else None
        tipo_cotizacion = sesion.tipo_cotizacion if sesion else "productos"
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
                    datos = await extraer_datos_etiqueta(
                        resp.content, _media_type(foto_url), tipo_cotizacion
                    )
                    # Un fallo del sistema NO es una foto "procesada": marcarla 'ok'
                    # hacia la vendedora como "no legible" es echarle la culpa a ella.
                    estado = "error" if es_error_sistema(datos) else "ok"
                    if estado == "ok":
                        await adjuntar_recorte(datos, resp.content)
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
