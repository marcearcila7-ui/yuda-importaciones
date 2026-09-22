from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import exigir_acceso_sesion, require_roles
from app.database import get_db
from app.models.cubicaje import TIPO_NOTA, TIPO_REPORTE, TIPO_RESPUESTA, CubicajeMensaje
from app.models.seguimiento import SeguimientoPedido
from app.models.sesion import Sesion
from app.models.user import User
from app.schemas.cubicaje import (
    CubicajeDetalle,
    CubicajeMensajeResponse,
    CubicajeNotaInput,
    CubicajeReporteInput,
    CubicajeRespuestaInput,
    CubicajeResumen,
)
from app.services.cubicaje_service import (
    LIMITE_MAX_CBM,
    LIMITE_MIN_CBM,
    RESULTADO_SOBRA,
    calcular_cbm_pedido,
    determinar_resultado,
)
from app.services.notificacion_service import avisar_cubicaje_a_bodega, avisar_cubicaje_a_vendedora

# Se monta en main.py bajo /api/v1
router = APIRouter(tags=["cubicaje"])


def _numero(sesion: Sesion) -> str:
    return f"YUDA-{sesion.fecha:%Y%m%d}-{sesion.id[:6].upper()}"


def _sesion_o_404(db: Session, sesion_id: str, usuario: User) -> Sesion:
    sesion = db.query(Sesion).filter(Sesion.id == sesion_id).first()
    if sesion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cotización no encontrada")
    exigir_acceso_sesion(db, sesion, usuario)
    return sesion


def _resumen_texto(
    resultado: str, cbm: float, referencia: str | None, cajas: int | None, espacio: float | None,
    cbm_ajustado: float | None = None,
) -> str:
    cbm_texto = f"{cbm_ajustado} m³ (bodega ajustó; el sistema calculó {cbm})" if cbm_ajustado is not None else f"{cbm} m³ calculados"
    if resultado == RESULTADO_SOBRA and referencia and cajas:
        return f"sobraron {cajas} caja(s) de «{referencia}» ({cbm_texto})"
    if resultado == "falta" and espacio is not None:
        return f"faltan {espacio} m³ para completar el contenedor ({cbm_texto})"
    return f"cubicaje ajustado: {cbm_texto}"


def _mensaje_response(m: CubicajeMensaje, autores: dict[str, User]) -> CubicajeMensajeResponse:
    autor = autores.get(m.autor_id)
    return CubicajeMensajeResponse(
        id=m.id,
        tipo=m.tipo,
        autor_id=m.autor_id,
        autor_nombre=autor.nombre if autor else None,
        mensaje=m.mensaje,
        cbm_calculado=m.cbm_calculado,
        cbm_ajustado=m.cbm_ajustado,
        resultado=m.resultado,
        referencia=m.referencia,
        cajas_afectadas=m.cajas_afectadas,
        espacio_restante_cbm=m.espacio_restante_cbm,
        created_at=m.created_at,
    )


@router.get("/sesiones/{sesion_id}/cubicaje", response_model=CubicajeDetalle)
def obtener_cubicaje(
    sesion_id: str,
    usuario: User = Depends(require_roles("admin", "vendedora", "bodega")),
    db: Session = Depends(get_db),
) -> CubicajeDetalle:
    """El cálculo en vivo del cubicaje (con lo que bodega ya inspeccionó) más
    todo el hilo de reportes/notas/respuestas de este pedido. Se usa con
    polling rápido en ambas apps -por eso va todo en una sola llamada."""
    sesion = _sesion_o_404(db, sesion_id, usuario)

    cbm, referencias = calcular_cbm_pedido(db, sesion)
    resumen = CubicajeResumen(
        cbm_calculado=cbm,
        limite_min=LIMITE_MIN_CBM,
        limite_max=LIMITE_MAX_CBM,
        resultado=determinar_resultado(cbm),
        referencias=referencias,
    )

    filas = (
        db.query(CubicajeMensaje)
        .filter(CubicajeMensaje.sesion_id == sesion_id)
        .order_by(CubicajeMensaje.created_at.asc())
        .all()
    )
    autor_ids = {m.autor_id for m in filas}
    autores = {u.id: u for u in db.query(User).filter(User.id.in_(autor_ids)).all()} if autor_ids else {}

    return CubicajeDetalle(resumen=resumen, mensajes=[_mensaje_response(m, autores) for m in filas])


@router.post("/bodega/pedidos/{sesion_id}/cubicaje/reporte", response_model=CubicajeMensajeResponse)
def enviar_reporte_cubicaje(
    sesion_id: str,
    datos: CubicajeReporteInput,
    usuario: User = Depends(require_roles("admin", "bodega")),
    db: Session = Depends(get_db),
) -> CubicajeMensaje:
    """Bodega manda un reporte de cubicaje a la vendedora: el cálculo lo hace
    siempre el servidor (nunca se confía en un número mandado por el
    cliente), y bodega solo aporta la referencia/cajas que sobraron (si
    aplica) y una nota opcional."""
    sesion = _sesion_o_404(db, sesion_id, usuario)

    if datos.resultado not in ("sobra", "falta", "ajustado"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Resultado inválido")

    cbm, referencias = calcular_cbm_pedido(db, sesion)

    referencia = None
    cajas_afectadas = None
    espacio_restante = None
    if datos.resultado == "sobra":
        if not datos.referencia or datos.referencia not in referencias:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Selecciona una referencia real de este pedido"
            )
        if not datos.cajas_afectadas or datos.cajas_afectadas <= 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Indica cuántas cajas sobraron")
        referencia = datos.referencia
        cajas_afectadas = datos.cajas_afectadas
    elif datos.resultado == "falta":
        espacio_restante = round(LIMITE_MAX_CBM - cbm, 4)

    # cbm_ajustado es la corrección a mano de bodega: solo se guarda si de
    # verdad difiere del calculado (si mandan el mismo número, no aporta nada
    # aparte y solo confundiría mostrar "bodega ajustó a lo mismo").
    cbm_ajustado = (
        round(datos.cbm_ajustado, 4)
        if datos.cbm_ajustado is not None and round(datos.cbm_ajustado, 4) != cbm
        else None
    )

    mensaje = CubicajeMensaje(
        sesion_id=sesion_id,
        tipo=TIPO_REPORTE,
        autor_id=usuario.id,
        mensaje=(datos.nota or "").strip() or None,
        cbm_calculado=cbm,
        cbm_ajustado=cbm_ajustado,
        resultado=datos.resultado,
        referencia=referencia,
        cajas_afectadas=cajas_afectadas,
        espacio_restante_cbm=espacio_restante,
    )
    db.add(mensaje)

    seg = db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == sesion_id).first()
    resumen_texto = _resumen_texto(datos.resultado, cbm, referencia, cajas_afectadas, espacio_restante, cbm_ajustado)
    avisar_cubicaje_a_vendedora(db, sesion_id, _numero(sesion), sesion.nombre_cliente, sesion.user_id, resumen_texto)
    db.commit()
    db.refresh(mensaje)

    return _mensaje_response(mensaje, {usuario.id: usuario})


@router.post("/bodega/pedidos/{sesion_id}/cubicaje/nota", response_model=CubicajeMensajeResponse)
def agregar_nota_cubicaje(
    sesion_id: str,
    datos: CubicajeNotaInput,
    usuario: User = Depends(require_roles("admin", "bodega")),
    db: Session = Depends(get_db),
) -> CubicajeMensaje:
    """Nota libre de bodega en el hilo de cubicaje (no recalcula nada, es solo
    contexto adicional para la vendedora). Cualquiera de bodega puede
    agregarla, no solo quien tiene el pedido asignado."""
    sesion = _sesion_o_404(db, sesion_id, usuario)
    texto = datos.mensaje.strip()
    if not texto:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Escribe algo para la nota")

    mensaje = CubicajeMensaje(sesion_id=sesion_id, tipo=TIPO_NOTA, autor_id=usuario.id, mensaje=texto)
    db.add(mensaje)
    avisar_cubicaje_a_vendedora(db, sesion_id, _numero(sesion), sesion.nombre_cliente, sesion.user_id, texto)
    db.commit()
    db.refresh(mensaje)

    return _mensaje_response(mensaje, {usuario.id: usuario})


@router.post("/sesiones/{sesion_id}/cubicaje/responder", response_model=CubicajeMensajeResponse)
def responder_cubicaje(
    sesion_id: str,
    datos: CubicajeRespuestaInput,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> CubicajeMensaje:
    """La vendedora (o Marcela) responde en el hilo de cubicaje. Avisa a
    quien tenga el pedido asignado en bodega (o a todo bodega/admin si nadie
    lo tiene asignado)."""
    sesion = _sesion_o_404(db, sesion_id, usuario)
    texto = datos.mensaje.strip()
    if not texto:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Escribe algo para responder")

    mensaje = CubicajeMensaje(sesion_id=sesion_id, tipo=TIPO_RESPUESTA, autor_id=usuario.id, mensaje=texto)
    db.add(mensaje)

    seg = db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == sesion_id).first()
    avisar_cubicaje_a_bodega(
        db, sesion_id, _numero(sesion), sesion.nombre_cliente,
        seg.bodega_asignado_a_id if seg else None, texto,
    )
    db.commit()
    db.refresh(mensaje)

    return _mensaje_response(mensaje, {usuario.id: usuario})
