import os

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

app = FastAPI(title="YUDA Importaciones")

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
