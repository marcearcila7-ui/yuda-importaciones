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


# ──────────────── API interna de Yuda Contable (búsqueda + estado de cuenta en vivo) ────────────────
# A diferencia de lo de arriba (que consulta la base de datos directo, solo
# tabla "clientes"), esto llama a la propia app de Yuda Contable: así el
# saldo, los pedidos y el PDF salen calculados exactamente como ella los ve
# ahí, sin duplicar esa lógica financiera acá. Token propio, distinto del de
# arriba (INTERNAL_API_TOKEN allá).

def _url_interna(ruta: str) -> str | None:
    if not settings.YUDA_CONTABLE_BASE_URL or not settings.YUDA_CONTABLE_API_TOKEN:
        return None
    base = settings.YUDA_CONTABLE_BASE_URL.rstrip("/")
    return f"{base}/api/interno/{ruta}"


def _headers_internos() -> dict[str, str]:
    # El token va en el header, no en la URL: esta ruta no tiene la
    # restricción del conector MCP (que solo se puede configurar con una
    # URL), así que no hace falta dejarlo expuesto en logs de acceso.
    return {"Authorization": f"Bearer {settings.YUDA_CONTABLE_API_TOKEN}"}


def buscar_clientes_contable(termino: str) -> list[dict] | None:
    """Clientes de Yuda Contable que coinciden con la sigla o el nombre
    (búsqueda en vivo, no una lista fija). None si la conexión no está
    configurada o falla -nunca lanza."""
    url = _url_interna("clientes")
    if not url or not termino.strip():
        return None
    try:
        resp = httpx.get(url, params={"q": termino.strip()}, headers=_headers_internos(), timeout=8)
        if resp.status_code != 200:
            return None
        return resp.json().get("clientes", [])
    except Exception:
        logger.exception("No se pudo buscar clientes en Yuda Contable (termino=%s)", termino)
        return None


def listar_todos_clientes_contable() -> list[dict] | None:
    """TODOS los clientes de Yuda Contable (hasta 1000), sin filtro -para
    comparar contra los que ya existen acá y armar la lista de "no
    sincronizados". None si la conexión no está configurada o falla."""
    url = _url_interna("clientes")
    if not url:
        return None
    try:
        resp = httpx.get(url, headers=_headers_internos(), timeout=15)
        if resp.status_code != 200:
            return None
        return resp.json().get("clientes", [])
    except Exception:
        logger.exception("No se pudo listar los clientes de Yuda Contable")
        return None


def obtener_estado_cuenta_contable(sigla: str) -> dict | None:
    """Estado de cuenta real de Yuda Contable (saldo, pedidos, abonos) para
    el cliente con esa sigla. None si no está configurado, no se encuentra,
    o falla la conexión."""
    url = _url_interna("estado-cuenta")
    if not url:
        return None
    try:
        resp = httpx.get(url, params={"cliente": sigla}, headers=_headers_internos(), timeout=8)
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        logger.exception("No se pudo traer el estado de cuenta de Yuda Contable (sigla=%s)", sigla)
        return None


def obtener_pdf_estado_cuenta_contable(sigla: str) -> bytes | None:
    """El PDF oficial del estado de cuenta, tal cual lo genera Yuda Contable.
    None si no está configurado, no se encuentra, o falla la conexión."""
    url = _url_interna("estado-cuenta")
    if not url:
        return None
    try:
        resp = httpx.get(
            url, params={"cliente": sigla, "formato": "pdf"}, headers=_headers_internos(), timeout=20
        )
        if resp.status_code != 200 or resp.headers.get("content-type") != "application/pdf":
            return None
        return resp.content
    except Exception:
        logger.exception("No se pudo traer el PDF del estado de cuenta de Yuda Contable (sigla=%s)", sigla)
        return None
