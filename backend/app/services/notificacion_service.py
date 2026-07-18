from sqlalchemy.orm import Session

from app.models.notificacion import (
    TIPO_ENVIO_VENDEDORA,
    TIPO_LISTO_PARA_ENVIO,
    TIPO_PEDIDO_CLIENTE,
    TIPO_PEDIDO_CONFIRMADO,
    Notificacion,
)
from app.models.user import RolUsuario, User


def _nombre_vendedora(db: Session, vendedor_id: str | None) -> str | None:
    """Nombre de la vendedora dueña de la cotización (para incluirlo en el aviso)."""
    if not vendedor_id:
        return None
    vend = db.query(User).filter(User.id == vendedor_id).first()
    return vend.nombre if vend else None


def avisar_listo_para_envio(
    db: Session, sesion_id: str, numero: str, cliente: str, vendedor_id: str | None = None
) -> None:
    """Crea un aviso para cada admin (Marcela): la cotización está lista para que
    cargue la naviera y el BL. Incluye la vendedora dueña. Evita duplicar si ya hay
    un aviso sin leer de esta cotización para ese admin.
    """
    vendedora = _nombre_vendedora(db, vendedor_id)
    quien = f" (vendedora: {vendedora})" if vendedora else ""
    admins = db.query(User).filter(User.rol == RolUsuario.admin, User.activo).all()
    for admin in admins:
        ya_existe = (
            db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == admin.id,
                Notificacion.sesion_id == sesion_id,
                Notificacion.tipo == TIPO_LISTO_PARA_ENVIO,
                Notificacion.leida.is_(False),
            )
            .first()
        )
        if ya_existe:
            continue
        db.add(
            Notificacion(
                usuario_id=admin.id,
                sesion_id=sesion_id,
                tipo=TIPO_LISTO_PARA_ENVIO,
                titulo="Cotización lista para envío",
                mensaje=(
                    f"La cotización {numero} de {cliente}{quien} está en bodega. "
                    "Es momento de cargar la naviera y el BL."
                ),
            )
        )


def avisar_pedido_cliente(
    db: Session, sesion_id: str, numero: str, cliente: str, vendedor_id: str
) -> None:
    """Crea un aviso cuando el cliente envía su pedido (cajas deseadas + notas)
    desde su portal. Lo reciben la vendedora dueña de la cotización y cada admin
    (Marcela), para que tengan visibilidad de lo que responde el cliente. Evita
    duplicar si ya hay un aviso sin leer de esta cotización para ese destinatario.
    """
    vendedora = _nombre_vendedora(db, vendedor_id)
    quien = f" (vendedora: {vendedora})" if vendedora else ""

    destinatarios = {vendedor_id}
    for admin in db.query(User).filter(User.rol == RolUsuario.admin, User.activo).all():
        destinatarios.add(admin.id)

    for usuario_id in destinatarios:
        ya_existe = (
            db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == usuario_id,
                Notificacion.sesion_id == sesion_id,
                Notificacion.tipo == TIPO_PEDIDO_CLIENTE,
                Notificacion.leida.is_(False),
            )
            .first()
        )
        if ya_existe:
            continue
        db.add(
            Notificacion(
                usuario_id=usuario_id,
                sesion_id=sesion_id,
                tipo=TIPO_PEDIDO_CLIENTE,
                titulo="Pedido del cliente recibido",
                mensaje=(
                    f"{cliente}{quien} envió su pedido de la cotización {numero} "
                    "(cantidades deseadas y notas). Ya puedes generar el pedido al proveedor."
                ),
            )
        )


# Mensajes del aviso Marcela → vendedora, según la etapa del envío.
_AVISOS_ENVIO_VENDEDORA = {
    "en_transito": (
        "Cotización despachada",
        "Tu cotización {numero} de {cliente} fue despachada: ya está en tránsito. "
        "Marcela cargó el BL y la naviera.",
    ),
    "entregado": (
        "Cotización entregada",
        "Tu cotización {numero} de {cliente} fue entregada al cliente. 🎉",
    ),
}


def avisar_envio_a_vendedora(
    db: Session, sesion_id: str, numero: str, cliente: str, vendedor_id: str | None, estado: str
) -> None:
    """Avisa a la vendedora dueña cuando Marcela actualiza el envío (despachado o
    entregado). Solo se envía a vendedoras activas (no a cotizaciones propias de un
    admin). Evita duplicar el mismo aviso sin leer."""
    plantilla = _AVISOS_ENVIO_VENDEDORA.get(estado)
    if plantilla is None or not vendedor_id:
        return
    vend = db.query(User).filter(User.id == vendedor_id).first()
    if vend is None or vend.rol != RolUsuario.vendedora or not vend.activo:
        return

    titulo, cuerpo = plantilla
    ya_existe = (
        db.query(Notificacion)
        .filter(
            Notificacion.usuario_id == vend.id,
            Notificacion.sesion_id == sesion_id,
            Notificacion.tipo == TIPO_ENVIO_VENDEDORA,
            Notificacion.titulo == titulo,
            Notificacion.leida.is_(False),
        )
        .first()
    )
    if ya_existe:
        return
    db.add(
        Notificacion(
            usuario_id=vend.id,
            sesion_id=sesion_id,
            tipo=TIPO_ENVIO_VENDEDORA,
            titulo=titulo,
            mensaje=cuerpo.format(numero=numero, cliente=cliente),
        )
    )


def avisar_pedido_confirmado(
    db: Session, sesion_id: str, numero: str, cliente: str, vendedor_id: str
) -> None:
    """Avisa a la vendedora dueña y a Marcela que el cliente confirmó las
    cantidades finales: ya se puede generar el pedido al proveedor. Evita duplicar
    si ya hay un aviso sin leer de esta cotización para ese destinatario."""
    destinatarios = {vendedor_id}
    for admin in db.query(User).filter(User.rol == RolUsuario.admin, User.activo).all():
        destinatarios.add(admin.id)

    for usuario_id in destinatarios:
        ya_existe = (
            db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == usuario_id,
                Notificacion.sesion_id == sesion_id,
                Notificacion.tipo == TIPO_PEDIDO_CONFIRMADO,
                Notificacion.leida.is_(False),
            )
            .first()
        )
        if ya_existe:
            continue
        db.add(
            Notificacion(
                usuario_id=usuario_id,
                sesion_id=sesion_id,
                tipo=TIPO_PEDIDO_CONFIRMADO,
                titulo="Pedido confirmado por el cliente",
                mensaje=(
                    f"{cliente} confirmó las cantidades de la cotización {numero}. "
                    "Ya puedes generar el pedido al proveedor."
                ),
            )
        )
