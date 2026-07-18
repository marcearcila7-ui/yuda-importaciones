import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    admin,
    auth,
    clientes,
    lotes,
    notificaciones,
    ocr,
    packing,
    pedidos,
    portal,
)
from app.core.config import settings
from app.core.logging_setup import configurar_logging
from app.core.security_headers import SecurityHeadersMiddleware

configurar_logging()
logger = logging.getLogger("app.main")

# Monitoreo de errores: solo se activa si hay SENTRY_DSN configurado (no-op en
# local y en tests). Si el paquete no está instalado, no rompe el arranque.
if settings.SENTRY_DSN:
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.SENTRY_ENVIRONMENT,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            send_default_pii=False,
        )
        logger.info("Sentry activado (entorno: %s)", settings.SENTRY_ENVIRONMENT)
    except Exception:
        logger.exception("No se pudo inicializar Sentry; el servicio sigue sin monitoreo")


async def _reanudar_lotes_interrumpidos() -> None:
    """Reanuda los lotes de OCR cortados por un reinicio del proceso web.

    Sin worker, el OCR corre en el proceso web; un reinicio (deploy/crash) lo
    interrumpiría y el lote quedaría 'procesando' colgado. Al arrancar, retomamos
    los que tienen fotos pendientes y cerramos los que ya estaban completos.
    Va dentro de un try amplio para que un problema de base al arrancar nunca
    tumbe el servicio (y para que no rompa los tests con base dummy)."""
    if settings.USE_WORKER:
        return
    try:
        from app.database import SessionLocal
        from app.models.lote import LoteItem, LoteOCR
        from app.services.lote_service import procesar_lote

        db = SessionLocal()
        try:
            ids = [
                lid for (lid,) in db.query(LoteOCR.id).filter(LoteOCR.estado == "procesando").all()
            ]
            a_reanudar, a_cerrar = [], []
            for lid in ids:
                pendiente = (
                    db.query(LoteItem.id)
                    .filter(LoteItem.lote_id == lid, LoteItem.estado == "pendiente")
                    .first()
                )
                (a_reanudar if pendiente else a_cerrar).append(lid)
            if a_cerrar:
                db.query(LoteOCR).filter(LoteOCR.id.in_(a_cerrar)).update(
                    {LoteOCR.estado: "completado"}, synchronize_session=False
                )
                db.commit()
        finally:
            db.close()
        for lid in a_reanudar:
            asyncio.create_task(procesar_lote(lid))
        if a_reanudar or a_cerrar:
            logger.info(
                "Arranque: %d lote(s) de OCR reanudados, %d cerrados",
                len(a_reanudar),
                len(a_cerrar),
            )
    except Exception:
        logger.exception("No se pudieron reanudar los lotes de OCR al arrancar")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _reanudar_lotes_interrumpidos()
    yield


app = FastAPI(title="YUDA Importaciones", lifespan=lifespan)

# Cabeceras de seguridad en todas las respuestas (HSTS, anti-clickjacking, nosniff)
app.add_middleware(SecurityHeadersMiddleware)

# Configuración de CORS a partir de los orígenes definidos en settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crea la carpeta de subidas si no existe y la expone como archivos estáticos
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Registro de los cuatro routers bajo el prefijo /api/v1
app.include_router(auth.router, prefix="/api/v1")
app.include_router(ocr.router, prefix="/api/v1")
app.include_router(packing.router, prefix="/api/v1")
app.include_router(pedidos.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(admin.historial_router, prefix="/api/v1")
app.include_router(lotes.router, prefix="/api/v1")
app.include_router(clientes.router, prefix="/api/v1")
app.include_router(portal.router, prefix="/api/v1")
app.include_router(notificaciones.router, prefix="/api/v1")


@app.get("/")
def root():
    """Endpoint de salud del sistema"""
    return {"status": "ok", "sistema": "YUDA Importaciones"}
