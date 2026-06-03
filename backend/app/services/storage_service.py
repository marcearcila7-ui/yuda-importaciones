from storage3 import create_client

from app.core.config import settings


def _storage():
    """Crea un cliente síncrono de Supabase Storage"""
    headers = {
        "apiKey": settings.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
    }
    return create_client(f"{settings.SUPABASE_URL}/storage/v1", headers, is_async=False)


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
    except Exception as e:
        print(f"Error subiendo la foto a Supabase Storage: {e}")
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
    except Exception as e:
        print(f"Error subiendo el Excel a Supabase Storage: {e}")
        raise
