"""Semáforo GLOBAL de OCR respaldado por Postgres (advisory locks).

El tope `OCR_CONCURRENCIA_GLOBAL` vale para TODO el sistema aunque haya varias
réplicas del backend: cada llamada de visión toma una de N "ranuras" mediante un
advisory lock de Postgres. Si un proceso muere, el lock cae solo al cerrarse la
sesión (no quedan ranuras trabadas). Si la base no es Postgres (tests) o algo
falla, cae a un semáforo en proceso para no bloquear el OCR.
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager

from app.core.config import settings
from app.database import engine

logger = logging.getLogger("app.ocr_limiter")

# Namespace fijo para las claves de advisory lock del OCR (evita choques con otros usos).
_NS = 918273
# Semáforo local de respaldo (tests / sin Postgres / ante fallo de base).
_local_sem: asyncio.Semaphore | None = None
# Máxima espera por una ranura antes de proceder igual (evita jobs colgados).
_MAX_ESPERA_SEG = 300


def _n() -> int:
    return max(1, settings.OCR_CONCURRENCIA_GLOBAL)


def _fallback_sem() -> asyncio.Semaphore:
    global _local_sem
    if _local_sem is None:
        _local_sem = asyncio.Semaphore(_n())
    return _local_sem


def _intentar_slot(n: int):
    """Abre una conexión y prueba las N claves. Si toma una, devuelve (conn, clave);
    si están todas ocupadas, cierra la conexión y devuelve None."""
    raw = engine.raw_connection()
    try:
        raw.driver_connection.autocommit = True  # evita transacciones ociosas colgadas
    except Exception:
        pass
    try:
        cur = raw.cursor()
        for k in range(1, n + 1):
            cur.execute("SELECT pg_try_advisory_lock(%s, %s)", (_NS, k))
            tomada = cur.fetchone()[0]
            if tomada:
                cur.close()
                return raw, k
        cur.close()
    except Exception:
        raw.close()
        raise
    raw.close()
    return None


def _liberar(raw, clave: int) -> None:
    try:
        cur = raw.cursor()
        cur.execute("SELECT pg_advisory_unlock(%s, %s)", (_NS, clave))
        cur.close()
    finally:
        raw.close()  # cerrar la sesión libera cualquier lock igualmente


@asynccontextmanager
async def slot_ocr():
    """Toma una ranura del tope global de OCR mientras dura el bloque `async with`."""
    n = _n()
    if engine.dialect.name != "postgresql":
        async with _fallback_sem():
            yield
        return

    loop = asyncio.get_event_loop()
    raw = None
    clave = None
    inicio = time.monotonic()
    try:
        while True:
            try:
                res = await loop.run_in_executor(None, _intentar_slot, n)
            except Exception:
                logger.exception("Fallo tomando ranura de OCR en la base; uso semáforo local")
                async with _fallback_sem():
                    yield
                return
            if res is not None:
                raw, clave = res
                break
            if time.monotonic() - inicio > _MAX_ESPERA_SEG:
                logger.warning("Sin ranura de OCR tras %ss; se procede igual", _MAX_ESPERA_SEG)
                yield
                return
            await asyncio.sleep(0.25)
        yield
    finally:
        if raw is not None and clave is not None:
            try:
                await loop.run_in_executor(None, _liberar, raw, clave)
            except Exception:
                logger.exception("Fallo liberando ranura de OCR")
