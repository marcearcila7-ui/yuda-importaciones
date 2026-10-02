"""Cálculo de cubicaje (CBM) de un pedido, ya con las correcciones de bodega
si las hay, frente al rango de un contenedor (68-72 m3, varía según la
mercancía). El cálculo en sí SIEMPRE lo hace el servidor -nunca se confía en
un número que mande el cliente- para que el historial de reportes quede
siempre consistente con los datos reales del pedido en ese momento."""
from sqlalchemy.orm import Session

from app.models.cubicaje import TIPO_REPORTE, CubicajeMensaje
from app.models.sesion import Sesion
from app.services.inspeccion_service import construir_inspeccion_sesion
from app.services.notificacion_service import avisar_cubicaje_a_vendedora

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


def _resumen_texto_automatico(resultado: str, cbm: float) -> str:
    if resultado == RESULTADO_FALTA:
        return f"faltan {round(LIMITE_MAX_CBM - cbm, 4)} m³ para completar el contenedor ({cbm} m³ calculados)"
    if resultado == RESULTADO_SOBRA:
        return (
            f"el pedido no cabe completo en el contenedor ({cbm} m³ calculados); "
            "falta que bodega indique qué producto y cuántas cajas se quedan afuera"
        )
    return f"cubicaje ajustado: {cbm} m³ calculados"


def generar_reporte_automatico(
    db: Session, sesion: Sesion, numero: str, usuario_id: str
) -> CubicajeMensaje | None:
    """Apenas bodega termina de revisar TODAS las órdenes de un pedido, le
    avisa sola a la vendedora con el cálculo de cubicaje -antes esto
    dependía de que alguien entrara aparte al panel de cubicaje y lo mandara
    a mano, y si nadie lo hacía, la vendedora nunca se enteraba.

    Para "ajustado" y "falta" no hace falta que bodega decida nada más, así
    que el reporte sale completo. Para "sobra" (no cabe) igual se le avisa a
    la vendedora de una vez, pero sin inventar qué producto o cuántas cajas
    se dejan afuera -eso bodega lo agrega después a mano en el mismo chat.

    No duplica: si ya existe un reporte para esta sesión (automático o
    manual), no manda uno nuevo."""
    ya_existe = (
        db.query(CubicajeMensaje)
        .filter(CubicajeMensaje.sesion_id == sesion.id, CubicajeMensaje.tipo == TIPO_REPORTE)
        .first()
    )
    if ya_existe is not None:
        return None

    cbm, _referencias = calcular_cbm_pedido(db, sesion)
    resultado = determinar_resultado(cbm)
    espacio_restante = round(LIMITE_MAX_CBM - cbm, 4) if resultado == RESULTADO_FALTA else None

    mensaje = CubicajeMensaje(
        sesion_id=sesion.id,
        tipo=TIPO_REPORTE,
        autor_id=usuario_id,
        cbm_calculado=cbm,
        resultado=resultado,
        espacio_restante_cbm=espacio_restante,
        automatico=True,
    )
    db.add(mensaje)
    avisar_cubicaje_a_vendedora(
        db, sesion.id, numero, sesion.nombre_cliente, sesion.user_id, _resumen_texto_automatico(resultado, cbm)
    )
    return mensaje
