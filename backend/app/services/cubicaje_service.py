"""Cálculo de cubicaje (CBM) de un pedido, ya con las correcciones de bodega
si las hay, frente al rango de un contenedor (68-72 m3, varía según la
mercancía). El cálculo en sí SIEMPRE lo hace el servidor -nunca se confía en
un número que mande el cliente- para que el historial de reportes quede
siempre consistente con los datos reales del pedido en ese momento."""
from sqlalchemy.orm import Session

from app.models.sesion import Sesion
from app.services.inspeccion_service import construir_inspeccion_sesion

# Rango típico de un contenedor: varía según la mercancía, pero 68-72 m3 es
# la referencia que usa bodega para decidir si un pedido cabe completo, sobra
# o falta espacio.
LIMITE_MIN_CBM = 68.0
LIMITE_MAX_CBM = 72.0

RESULTADO_SOBRA = "sobra"
RESULTADO_FALTA = "falta"
RESULTADO_AJUSTADO = "ajustado"


def _valor(campo) -> float:
    v = campo.corregido if campo.corregido is not None else campo.original
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def calcular_cbm_pedido(db: Session, sesion: Sesion) -> tuple[float, list[str]]:
    """CBM total del pedido (con correcciones de bodega ya fusionadas) y la
    lista de referencias distintas que tiene, en el orden en que aparecen."""
    inspeccion = construir_inspeccion_sesion(db, sesion)
    total = 0.0
    referencias: list[str] = []

    for item in inspeccion.items:
        largo = _valor(item.largo_cm)
        ancho = _valor(item.ancho_cm)
        alto = _valor(item.alto_cm)
        ctns = _valor(item.cajas)
        total += (largo * ancho * alto / 1_000_000) * ctns

        for extra in item.cajas_extra:
            e_largo = extra.largo_cm if extra.largo_cm is not None else largo
            e_ancho = extra.ancho_cm if extra.ancho_cm is not None else ancho
            e_alto = extra.alto_cm if extra.alto_cm is not None else alto
            total += ((e_largo or 0) * (e_ancho or 0) * (e_alto or 0) / 1_000_000) * (extra.ctns or 0)

        ref = item.referencia.corregido or item.referencia.original
        if ref and ref not in referencias:
            referencias.append(str(ref))

    return round(total, 4), referencias


def determinar_resultado(cbm: float) -> str:
    if cbm < LIMITE_MIN_CBM:
        return RESULTADO_FALTA
    return RESULTADO_AJUSTADO if cbm <= LIMITE_MAX_CBM else RESULTADO_SOBRA
