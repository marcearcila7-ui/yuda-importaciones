from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.cubicaje import CubicajeVisto
from app.models.notificacion import (
    TIPO_AVISO_CLIENTE_FALLIDO,
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
    TIPO_PENDIENTE_BL,
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
    push: bool = True,
) -> None:
    """Crea el aviso en la campanita y, de paso, intenta mandarlo como
    notificación push al navegador (si el usuario está suscrito). El push es
    mejor esfuerzo: si falla o no hay suscripción, el aviso en la campanita
    queda de todas formas.

    push=False cuando ya se sabe que el destinatario está viendo esto en
    vivo en pantalla (ver _esta_viendo_cubicaje): la campanita igual se
    crea, pero no tiene sentido mandarle un push por algo que ya está
    mirando."""
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
    if push:
        enviar_push(db, usuario_id, titulo, mensaje, sesion_id)


# Cada cuánto manda el heartbeat el frontend (ver POST .../cubicaje/visto):
# con margen sobre eso, para no tratar como "se fue" a alguien cuyo heartbeat
# solo se demoró un poco en llegar.
_VISTO_VIGENCIA = timedelta(seconds=20)


def _esta_viendo_cubicaje(db: Session, usuario_id: str, sesion_id: str) -> bool:
    """True si este usuario tiene el chat de cubicaje de esta sesión abierto
    y en foco ahora mismo (heartbeat reciente)."""
    visto = (
        db.query(CubicajeVisto)
        .filter(CubicajeVisto.sesion_id == sesion_id, CubicajeVisto.usuario_id == usuario_id)
        .first()
    )
    if visto is None:
        return False
    visto_en = visto.visto_en if visto.visto_en.tzinfo else visto.visto_en.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - visto_en < _VISTO_VIGENCIA


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
    """Crea un aviso para cada admin (Marcela): la cotización está lista para
    despachar (cargar la naviera). Incluye la vendedora dueña. Evita duplicar
    si ya hay un aviso sin leer de esta cotización para ese admin.

    OJO: acá NO se menciona el BL a propósito -ese número solo existe unos 20
    días después de que la mercancía se despacha (en_transito), mucho más
    adelante que este momento (mercancía recién llegando a bodega). Ver
    avisar_pendiente_bl más abajo para ese aviso, en el momento correcto.
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
            "Es momento de cargar la naviera.",
        )


def avisar_pendiente_bl(db: Session, sesion_id: str, numero: str, cliente: str) -> None:
    """Crea un aviso para cada admin (Marcela) apenas el pedido se despacha
    (pasa a "en_transito"): el BL es un dato que solo existe unos 20 días
    después de despachar, así que este aviso es "ya salió, en unos 20 días
    deberías tener el BL para cargarlo" -no una urgencia inmediata, un
    recordatorio de que este pedido va a necesitar esa carga más adelante.
    Evita duplicar si ya hay un aviso sin leer de esta cotización para ese admin.
    """
    admins = db.query(User).filter(User.rol == RolUsuario.admin, User.activo).all()
    for admin in admins:
        ya_existe = (
            db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == admin.id,
                Notificacion.sesion_id == sesion_id,
                Notificacion.tipo == TIPO_PENDIENTE_BL,
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
            TIPO_PENDIENTE_BL,
            "Pedido despachado: pendiente de BL",
            f"La cotización {numero} de {cliente} ya se despachó. "
            "En unos 20 días deberías tener el BL para cargarlo aquí.",
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
            push=not _esta_viendo_cubicaje(db, usuario_id, sesion_id),
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
            push=not _esta_viendo_cubicaje(db, usuario_id, sesion_id),
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
    db: Session,
    sesion_id: str,
    numero: str,
    cliente: str,
    vendedor_id: str | None,
    bodega_asignado_id: str | None = None,
    resumen_observaciones: str | None = None,
) -> None:
    """Avisa a la vendedora dueña, a Marcela y a quien de bodega tenga
    asignado este pedido que el cliente aprobó, desde su portal, el despacho
    que bodega dejó listo: ya se puede mandar el contenedor por barco. Evita
    duplicar si ya hay un aviso sin leer de esta cotización para ese
    destinatario."""
    destinatarios = {vendedor_id} if vendedor_id else set()
    if bodega_asignado_id:
        destinatarios.add(bodega_asignado_id)
    for admin in db.query(User).filter(User.rol == RolUsuario.admin, User.activo).all():
        destinatarios.add(admin.id)

    cuerpo = f"{cliente} aprobó el despacho de la cotización {numero}. Ya se puede mandar por barco."
    if resumen_observaciones:
        cuerpo += f" Observaciones del cliente: {resumen_observaciones}"

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
        _crear(db, usuario_id, sesion_id, TIPO_DESPACHO_APROBADO, "Cliente aprobó el despacho", cuerpo)


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
