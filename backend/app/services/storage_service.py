import logging

from storage3 import create_client

from app.core.config import settings

logger = logging.getLogger(__name__)


def _storage():
    """Crea un cliente síncrono de Supabase Storage"""
    headers = {
        "apiKey": settings.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
    }
    return create_client(f"{settings.SUPABASE_URL}/storage/v1", headers, is_async=False)


def ruta_desde_url(url: str | None, bucket: str) -> str | None:
    """Extrae la ruta dentro del bucket a partir de la URL pública, o None."""
    if not url:
        return None
    marcador = f"/object/public/{bucket}/"
    i = url.find(marcador)
    return url[i + len(marcador):] if i != -1 else None


def borrar_archivos(bucket: str, rutas: list[str | None]) -> None:
    """Borra archivos de un bucket. Best-effort: nunca lanza (solo loguea), para
    no romper una operación (p. ej. eliminar cotización) si el storage falla."""
    limpias = [r for r in rutas if r]
    if not limpias:
        return
    try:
        _storage().from_(bucket).remove(limpias)
    except Exception:
        logger.exception("No se pudieron borrar %d archivo(s) del bucket %s", len(limpias), bucket)


def subir_foto(imagen_bytes: bytes, nombre_archivo: str, content_type: str) -> str:
    """Sube una foto al bucket 'fotos' y devuelve su URL pública"""
    try:
        storage = _storage()
        storage.from_("fotos").upload(
            nombre_archivo,
            imagen_bytes,
            {"content-type": content_type, "upsert": "true"},
        )
        return f"{settings.SUPABASE_URL}/storage/v1/object/public/fotos/{nombre_archivo}"
    except Exception:
        logger.exception("Error subiendo la foto a Supabase Storage")
        raise


def subir_excel(archivo_bytes: bytes, nombre_archivo: str) -> str:
    """Sube un Excel al bucket 'pedidos' y devuelve su URL pública"""
    try:
        storage = _storage()
        storage.from_("pedidos").upload(
            nombre_archivo,
            archivo_bytes,
            {
                "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "upsert": "true",
            },
        )
        return f"{settings.SUPABASE_URL}/storage/v1/object/public/pedidos/{nombre_archivo}"
    except Exception:
        logger.exception("Error subiendo el Excel a Supabase Storage")
        raise


def subir_pdf(archivo_bytes: bytes, nombre_archivo: str) -> str:
    """Sube un PDF al bucket 'pedidos' y devuelve su URL pública"""
    try:
        storage = _storage()
        storage.from_("pedidos").upload(
            nombre_archivo,
            archivo_bytes,
            {"content-type": "application/pdf", "upsert": "true"},
        )
        return f"{settings.SUPABASE_URL}/storage/v1/object/public/pedidos/{nombre_archivo}"
    except Exception:
        logger.exception("Error subiendo el PDF a Supabase Storage")
        raise
