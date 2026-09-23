from sqlalchemy.orm import Session

from app.models.notificacion import (
    TIPO_AVISO_CLIENTE_FALLIDO,
    TIPO_BODEGA_ENVIO_A_VENDEDORA,
    TIPO_CUBICAJE_BODEGA,
    TIPO_CUBICAJE_VENDEDORA,
    TIPO_DESPACHO_APROBADO,
    TIPO_ENVIO_VENDEDORA,
    TIPO_LISTO_PARA_ENVIO,
    TIPO_INSPECCION_BODEGA_ACTUALIZADA,
    TIPO_ORDEN_ACTUALIZADA_BODEGA,
    TIPO_PEDIDO_CLIENTE,
    TIPO_PEDIDO_CONFIRMADO,
    TIPO_PEDIDO_REGENERADO_TRAS_REVISION,
    Notificacion,
)
from app.models.user import RolUsuario, User
from app.services.push_service import enviar_push


def _crear(
    db: Session,
    usuario_id: str,
    sesion_id: str,
    tipo: str,
    titulo: str,
    mensaje: str,
    ref_id: str | None = None,
) -> None:
    """Crea el aviso en la campanita y, de paso, intenta mandarlo como
    notificación push al navegador (si el usuario está suscrito). El push es
    mejor esfuerzo: si falla o no hay suscripción, el aviso en la campanita
    queda de todas formas."""
    db.add(
        Notificacion(
            usuario_id=usuario_id,
            sesion_id=sesion_id,
            ref_id=ref_id,
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
        )
    )
    enviar_push(db, usuario_id, titulo, mensaje, sesion_id)


def avisar_fallo_aviso_cliente(
    db: Session, sesion_id: str, cliente_nombre: str, canal: str, motivo: str
) -> None:
    """Un correo o WhatsApp automático a un cliente falló (Brevo/Lucid Bot
    caídos, sin configurar, o el cliente sin teléfono/correo). Antes esto
    solo quedaba en el log del servidor: nadie del equipo se enteraba de que
    un cliente se quedó sin ese aviso. Avisa a cada admin activo.

    Hace su propio commit a propósito: se llama desde dentro de un `except`,
    después de que ya falló una llamada de red (Brevo/Lucid Bot), en rutas
    que no vuelven a comitear después de ese punto -sin esto, el aviso
    quedaría solo agregado a la sesión y se perdería al cerrarla."""
    for admin in db.query(User).filter(User.rol == RolUsuario.admin, User.activo).all():
        _crear(
            db,
            admin.id,
            sesion_id,
            TIPO_AVISO_CLIENTE_FALLIDO,
            f"No se pudo avisar a {cliente_nombre} por {canal}",
            motivo,
        )
    db.commit()


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
        _crear(
            db,
            admin.id,
            sesion_id,
            TIPO_LISTO_PARA_ENVIO,
            "Cotización lista para envío",
            f"La cotización {numero} de {cliente}{quien} está en bodega. "
            "Es momento de cargar la naviera y el BL.",
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
        _crear(
            db,
            usuario_id,
            sesion_id,
            TIPO_PEDIDO_CLIENTE,
            "Pedido del cliente recibido",
            f"{cliente}{quien} envió su pedido de la cotización {numero} "
            "(cantidades deseadas y notas). Ya puedes generar el pedido al proveedor.",
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
    _crear(db, vend.id, sesion_id, TIPO_ENVIO_VENDEDORA, titulo, cuerpo.format(numero=numero, cliente=cliente))


def avisar_bodega_envio_a_vendedora(
    db: Session, sesion_id: str, numero: str, cliente: str, vendedor_id: str | None
) -> None:
    """Bodega, a propósito (botón aparte de "Enviar al cliente"), le avisa a la
    vendedora dueña que ya le mandó al cliente la inspección para su
    aprobación -para que la revise sin depender de que Marcela se lo cuente.
    No evita duplicar por tipo+sesión: bodega puede querer volver a avisar si
    corrigió algo después del primer envío."""
    if not vendedor_id:
        return
    vend = db.query(User).filter(User.id == vendedor_id).first()
    if vend is None or vend.rol != RolUsuario.vendedora or not vend.activo:
        return

    _crear(
        db,
        vend.id,
        sesion_id,
        TIPO_BODEGA_ENVIO_A_VENDEDORA,
        "Bodega le envió la inspección a tu cliente",
        f"Bodega le mandó a {cliente} (cotización {numero}) las fotos y datos de la "
        "inspección para que apruebe el despacho. Revisa el seguimiento de la cotización "
        "para ver exactamente lo mismo que le llegó al cliente.",
    )


def avisar_cubicaje_a_vendedora(
    db: Session, sesion_id: str, numero: str, cliente: str, vendedor_id: str | None, resumen: str
) -> None:
    """Bodega mandó un reporte o nota de cubicaje sobre este pedido: aviso
    instantáneo (campanita) para la vendedora dueña y Marcela. No evita
    duplicar por tipo+sesión: cada entrada del hilo de cubicaje es su propio
    aviso, igual que las correcciones de inspección."""
    destinatarios = {vendedor_id} if vendedor_id else set()
    for admin in db.query(User).filter(User.rol == RolUsuario.admin, User.activo).all():
        destinatarios.add(admin.id)

    for usuario_id in destinatarios:
        _crear(
            db,
            usuario_id,
            sesion_id,
            TIPO_CUBICAJE_BODEGA,
            "Reporte de cubicaje",
            f"Bodega actualizó el cubicaje de {cliente} (cotización {numero}): {resumen}",
        )


def avisar_cubicaje_a_bodega(
    db: Session,
    sesion_id: str,
    numero: str,
    cliente: str,
    bodega_asignado_a_id: str | None,
    mensaje: str,
) -> None:
    """La vendedora respondió en el hilo de cubicaje: aviso instantáneo
    (campanita) para quien tiene asignado el pedido en bodega, o para todo
    bodega/admin activo si nadie lo tiene asignado (mismo criterio de
    visibilidad que la cola de bodega sin asignar)."""
    if bodega_asignado_a_id:
        destinatarios = {bodega_asignado_a_id}
    else:
        destinatarios = {
            u.id
            for u in db.query(User)
            .filter(User.rol.in_([RolUsuario.admin, RolUsuario.bodega]), User.activo)
            .all()
        }

    for usuario_id in destinatarios:
        _crear(
            db,
            usuario_id,
            sesion_id,
            TIPO_CUBICAJE_VENDEDORA,
            "Respuesta de la vendedora en cubicaje",
            f"{cliente} (cotización {numero}): {mensaje}",
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
        _crear(
            db,
            usuario_id,
            sesion_id,
            TIPO_PEDIDO_CONFIRMADO,
            "Pedido confirmado por el cliente",
            f"{cliente} confirmó las cantidades de la cotización {numero}. "
            "Ya puedes generar el pedido al proveedor.",
        )


def avisar_despacho_aprobado(
    db: Session, sesion_id: str, numero: str, cliente: str, vendedor_id: str | None
) -> None:
    """Avisa a la vendedora dueña y a Marcela que el cliente aprobó, desde su
    portal, el despacho que bodega dejó listo: ya se puede mandar el
    contenedor por barco. Evita duplicar si ya hay un aviso sin leer de esta
    cotización para ese destinatario."""
    destinatarios = {vendedor_id} if vendedor_id else set()
    for admin in db.query(User).filter(User.rol == RolUsuario.admin, User.activo).all():
        destinatarios.add(admin.id)

    for usuario_id in destinatarios:
        ya_existe = (
            db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == usuario_id,
                Notificacion.sesion_id == sesion_id,
                Notificacion.tipo == TIPO_DESPACHO_APROBADO,
                Notificacion.leida.is_(False),
            )
            .first()
        )
        if ya_existe:
            continue
        _crear(
            db,
            usuario_id,
            sesion_id,
            TIPO_DESPACHO_APROBADO,
            "Cliente aprobó el despacho",
            f"{cliente} aprobó el despacho de la cotización {numero}. Ya se puede mandar por barco.",
        )


def avisar_orden_actualizada_bodega(
    db: Session, sesion_id: str, numero: str, cliente: str, vendedor_id: str | None, supplier: str
) -> None:
    """Avisa a la vendedora dueña y a Marcela que bodega corrigió la orden a un
    proveedor con las cantidades que realmente llegaron. No evita duplicar por
    tipo+sesión (a diferencia de los demás avisos), porque bodega puede corregir
    más de un proveedor de la misma cotización y cada corrección merece su
    propio aviso; si ya hay uno igual sin leer para el mismo proveedor, no se
    repite."""
    destinatarios = {vendedor_id} if vendedor_id else set()
    for admin in db.query(User).filter(User.rol == RolUsuario.admin, User.activo).all():
        destinatarios.add(admin.id)

    for usuario_id in destinatarios:
        ya_existe = (
            db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == usuario_id,
                Notificacion.sesion_id == sesion_id,
                Notificacion.tipo == TIPO_ORDEN_ACTUALIZADA_BODEGA,
                Notificacion.ref_id == supplier,
                Notificacion.leida.is_(False),
            )
            .first()
        )
        if ya_existe:
            continue
        _crear(
            db,
            usuario_id,
            sesion_id,
            TIPO_ORDEN_ACTUALIZADA_BODEGA,
            "Bodega actualizó una orden con lo que llegó",
            f"Bodega revisó la orden de «{supplier}» de la cotización {numero} "
            f"({cliente}) y la corrigió con las cantidades reales. Revisa y avísale al cliente.",
            ref_id=supplier,
        )


def avisar_pedido_regenerado_tras_revision(
    db: Session, sesion_id: str, numero: str, cliente: str, vendedor_id: str | None, supplier: str
) -> None:
    """Avisa a la vendedora dueña y a Marcela que se regeneró el pedido a un
    proveedor que bodega YA había revisado: esa revisión de cantidades reales
    quedó invalidada (bodega tiene que volver a contarla). No evita duplicar
    por tipo+sesión (igual que orden_actualizada_bodega): puede pasar más de
    una vez y cada una merece su propio aviso; si ya hay uno igual sin leer
    para el mismo proveedor, no se repite."""
    destinatarios = {vendedor_id} if vendedor_id else set()
    for admin in db.query(User).filter(User.rol == RolUsuario.admin, User.activo).all():
        destinatarios.add(admin.id)

    for usuario_id in destinatarios:
        ya_existe = (
            db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == usuario_id,
                Notificacion.sesion_id == sesion_id,
                Notificacion.tipo == TIPO_PEDIDO_REGENERADO_TRAS_REVISION,
                Notificacion.ref_id == supplier,
                Notificacion.leida.is_(False),
            )
            .first()
        )
        if ya_existe:
            continue
        _crear(
            db,
            usuario_id,
            sesion_id,
            TIPO_PEDIDO_REGENERADO_TRAS_REVISION,
            "Se regeneró un pedido ya revisado por bodega",
            f"Se volvió a generar el pedido de «{supplier}» de la cotización {numero} "
            f"({cliente}), que bodega ya había revisado. Esa revisión se perdió: "
            "bodega tiene que volver a contar las cantidades reales de este proveedor.",
            ref_id=supplier,
        )


def avisar_inspeccion_actualizada(
    db: Session, sesion_id: str, numero: str, cliente: str, vendedor_id: str | None
) -> None:
    """Avisa a la vendedora dueña y a Marcela que bodega guardó correcciones de
    inspección sobre la cotización del cliente (cantidades reales, medidas,
    fotos/video de evidencia). No evita duplicar por tipo+sesión: bodega puede
    guardar varias veces mientras va inspeccionando producto por producto, y
    cada guardado merece su propio aviso; si ya hay uno igual sin leer, no se
    repite."""
    destinatarios = {vendedor_id} if vendedor_id else set()
    for admin in db.query(User).filter(User.rol == RolUsuario.admin, User.activo).all():
        destinatarios.add(admin.id)

    for usuario_id in destinatarios:
        ya_existe = (
            db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == usuario_id,
                Notificacion.sesion_id == sesion_id,
                Notificacion.tipo == TIPO_INSPECCION_BODEGA_ACTUALIZADA,
                Notificacion.leida.is_(False),
            )
            .first()
        )
        if ya_existe:
            continue
        _crear(
            db,
            usuario_id,
            sesion_id,
            TIPO_INSPECCION_BODEGA_ACTUALIZADA,
            "Bodega actualizó la inspección de la cotización",
            f"Bodega guardó correcciones de inspección en la cotización {numero} "
            f"({cliente}): cantidades reales, medidas o evidencia. Revísalas.",
        )
