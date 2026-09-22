"""Lectura de datos de contacto (teléfono/WhatsApp) de Yuda Contable, la app
de contabilidad de Marcela: bases de datos separadas, pero el cliente
correspondiente se identifica por "sigla" (la misma que Marcela ya escribe a
mano en la ficha del cliente para cruzarlo con esa app).

Es de SOLO LECTURA y se limita a la tabla "clientes" de Yuda Contable -nunca
toca facturas, saldos ni abonos, aunque la llave configurada tenga acceso a
eso. Nunca escribe nada allá."""
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def buscar_contacto_por_sigla(sigla: str | None) -> dict | None:
    """{"telefono": ..., "whatsapp": ...} del cliente con esa sigla en Yuda
    Contable, o None si no hay sigla, no está configurada la conexión, o no
    se encuentra. Nunca lanza: si Yuda Contable no responde, simplemente no
    hay dato de contacto que heredar."""
    if not sigla or not settings.CONTABLE_SUPABASE_URL or not settings.CONTABLE_SUPABASE_SERVICE_KEY:
        return None
    try:
        resp = httpx.get(
            f"{settings.CONTABLE_SUPABASE_URL}/rest/v1/clientes",
            params={"select": "telefono,whatsapp", "sigla": f"eq.{sigla}"},
            headers={
                "apikey": settings.CONTABLE_SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {settings.CONTABLE_SUPABASE_SERVICE_KEY}",
            },
            timeout=8,
        )
        if resp.status_code != 200:
            return None
        filas = resp.json()
        if not filas:
            return None
        return {"telefono": filas[0].get("telefono"), "whatsapp": filas[0].get("whatsapp")}
    except Exception:
        logger.exception("No se pudo consultar el contacto en Yuda Contable (sigla=%s)", sigla)
        return None
