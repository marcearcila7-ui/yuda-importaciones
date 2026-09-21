from sqlalchemy.orm import Session

from app.models.pedido_bodega_actividad import PedidoBodegaActividad


def registrar_actividad_bodega(
    db: Session, sesion_id: str, usuario_id: str, tipo: str, detalle: str | None = None
) -> None:
    """Deja constancia de una acción sobre un pedido ya en bodega (asignación,
    orden actualizada, inspección corregida, envío confirmado). No hace commit:
    queda dentro de la misma transacción de quien la llama."""
    db.add(
        PedidoBodegaActividad(sesion_id=sesion_id, usuario_id=usuario_id, tipo=tipo, detalle=detalle)
    )
