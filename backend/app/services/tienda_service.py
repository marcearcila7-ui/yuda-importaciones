"""Cálculos y alertas de los pedidos a tiendas (Módulo Contadora)."""
from datetime import date

from sqlalchemy.orm import Session

from app.models.notificacion import TIPO_ALERTA_PAGO_TIENDA, Notificacion
from app.models.tienda import (
    DIAS_AVISO_PAGO_70,
    ESTADO_PAGADO,
    ESTADO_PARCIAL,
    ESTADO_PENDIENTE,
    PCT_DEPOSITO,
    PCT_SALDO,
    PedidoTienda,
)
from app.models.user import RolUsuario, User


def _f(v) -> float:
    return float(v or 0)


def estado_pedido(p: PedidoTienda) -> str:
    if p.fecha_pago_70:
        return ESTADO_PAGADO
    if p.fecha_pago_30:
        return ESTADO_PARCIAL
    return ESTADO_PENDIENTE


def _dias_para_pago_70(p: PedidoTienda, hoy: date) -> int | None:
    if p.fecha_estimada_pago_70 is None:
        return None
    return (p.fecha_estimada_pago_70 - hoy).days


def hay_alerta_pago_70(p: PedidoTienda, hoy: date) -> bool:
    """True si falta pagar el 70% y la fecha estimada está a <= 7 días (o vencida)."""
    if p.fecha_pago_70 is not None or p.fecha_estimada_pago_70 is None:
        return False
    return (p.fecha_estimada_pago_70 - hoy).days <= DIAS_AVISO_PAGO_70


def construir_response(p: PedidoTienda, db: Session, hoy: date | None = None) -> dict:
    """Combina los campos guardados con los montos y el estado calculados."""
    hoy = hoy or date.today()
    total = _f(p.monto_total)
    empleada = (
        db.query(User).filter(User.id == p.empleada_id).first() if p.empleada_id else None
    )
    return {
        "id": p.id,
        "nombre_tienda": p.nombre_tienda,
        "fecha_pedido": p.fecha_pedido,
        "monto_total": round(total, 2),
        "monto_30": round(total * PCT_DEPOSITO, 2),
        "monto_70": round(total * PCT_SALDO, 2),
        "monto_comision": round(total * _f(p.pct_comision_tienda) / 100, 2),
        "fecha_pago_30": p.fecha_pago_30,
        "fecha_estimada_entrega": p.fecha_estimada_entrega,
        "fecha_real_entrega": p.fecha_real_entrega,
        "fecha_estimada_pago_70": p.fecha_estimada_pago_70,
        "fecha_pago_70": p.fecha_pago_70,
        "pct_comision_tienda": _f(p.pct_comision_tienda),
        "empleada_id": p.empleada_id,
        "empleada_nombre": empleada.nombre if empleada else None,
        "notas": p.notas,
        "estado": estado_pedido(p),
        "dias_para_pago_70": _dias_para_pago_70(p, hoy),
        "alerta_pago_70": hay_alerta_pago_70(p, hoy),
        "created_at": p.created_at,
    }


def revisar_alertas_pago_70(db: Session, hoy: date | None = None) -> int:
    """Crea avisos in-app para la(s) contadora(s) por pedidos con el 70% por
    vencer/vencido y sin pagar. Idempotente: un aviso por pedido y contadora.
    Devuelve cuántos avisos nuevos creó."""
    hoy = hoy or date.today()
    contadoras = (
        db.query(User).filter(User.rol == RolUsuario.contadora, User.activo.is_(True)).all()
    )
    if not contadoras:
        return 0

    pedidos = db.query(PedidoTienda).filter(PedidoTienda.fecha_pago_70.is_(None)).all()
    creados = 0
    for p in pedidos:
        if not hay_alerta_pago_70(p, hoy):
            continue
        dias = (p.fecha_estimada_pago_70 - hoy).days
        cuerpo = (
            f"El 70% de {p.nombre_tienda} "
            + ("está vencido" if dias < 0 else f"vence en {dias} día(s)")
            + f". Saldo aprox: ¥{round(_f(p.monto_total) * PCT_SALDO, 2)}."
        )
        for c in contadoras:
            existe = (
                db.query(Notificacion)
                .filter(
                    Notificacion.usuario_id == c.id,
                    Notificacion.tipo == TIPO_ALERTA_PAGO_TIENDA,
                    Notificacion.ref_id == p.id,
                )
                .first()
            )
            if existe:
                continue
            db.add(
                Notificacion(
                    usuario_id=c.id,
                    ref_id=p.id,
                    tipo=TIPO_ALERTA_PAGO_TIENDA,
                    titulo="Pago del 70% a tienda por vencer",
                    mensaje=cuerpo,
                )
            )
            creados += 1
    if creados:
        db.commit()
    return creados
