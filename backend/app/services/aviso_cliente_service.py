"""Avisos al cliente por fuera del portal: correo transaccional (Brevo) y
WhatsApp (Lucid Bot, construido sobre ChatRace: api.chatrace.com).

Todo acá es best-effort a propósito: si Brevo o Lucid Bot fallan, no están
configurados, o el cliente no tiene teléfono/correo, se registra en el log
pero NUNCA se interrumpe el flujo de bodega o de Marcela por un aviso que no
salió.

WhatsApp tiene dos modos:
- Texto libre (`send/text`): solo funciona dentro de la ventana de 24h desde
  el último mensaje del contacto al bot. Es el modo por defecto.
- Plantilla (flow de Lucid Bot, LUCIDBOT_FLOW_APROBAR_DESPACHO): obligatorio
  fuera de esa ventana. Se dejan las variables en custom fields del contacto
  y se dispara el flow, que es donde vive la plantilla aprobada de WhatsApp.
"""
import logging
import re
from datetime import date, datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.models.cliente import Cliente
from app.services.notificacion_service import avisar_fallo_aviso_cliente

logger = logging.getLogger("app.aviso_cliente")


def _avisar_fallo(db: Session, sesion_id: str, cliente: Cliente, numero: str, canal: str, exc: Exception) -> None:
    """Además del log, deja un aviso para cada admin: antes esto solo
    quedaba en el servidor y nadie del equipo se enteraba de que un cliente
    se quedó sin ese correo/WhatsApp."""
    avisar_fallo_aviso_cliente(
        db, sesion_id, cliente.nombre, canal, f"Pedido {numero}. Motivo: {exc}"
    )

_MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _link_portal(sesion_id: str) -> str:
    """URL de la cotización en el portal de clientes (dominio propio, ruta singular)."""
    return f"{settings.PORTAL_URL}/portal/cotizacion/{sesion_id}"


def _link_portal_magico(cliente_id: str, sesion_id: str, expira: datetime) -> str:
    """Enlace de un solo destino que entra directo a la cotización sin pedir
    contraseña (útil en avisos automáticos: el cliente no siempre la recuerda,
    y no queremos exponer ni resetear su contraseña real para mandarla por
    WhatsApp/correo). Vale hasta `expira` -mismo plazo que tiene para aprobar
    el despacho, así el enlace no queda vivo para siempre."""
    ahora = datetime.now(timezone.utc)
    vigencia = expira - ahora
    token = create_access_token(
        {"sub": cliente_id, "tipo": "cliente_magic", "sesion_id": sesion_id},
        expires_delta=vigencia if vigencia.total_seconds() > 0 else None,
    )
    return f"{settings.PORTAL_URL}/portal/entrar?token={token}"


def _formatear_plazo(momento: datetime) -> str:
    """'2026-09-19T09:31:01+00:00' -> '19 de septiembre a las 9:31 am'"""
    hora12 = momento.hour % 12 or 12
    ampm = "am" if momento.hour < 12 else "pm"
    return f"{momento.day} de {_MESES[momento.month - 1]} a las {hora12}:{momento.minute:02d} {ampm}"


def formatear_fecha_legible(fecha_iso: str) -> str:
    """'2026-09-19' -> '19 de septiembre de 2026'"""
    try:
        y, m, d = (int(p) for p in fecha_iso.split("-"))
        return f"{d} de {_MESES[m - 1]} de {y}"
    except (ValueError, IndexError):
        return fecha_iso


def _enviar_correo_brevo(destinatario: Cliente, asunto: str, html: str) -> None:
    # email_contacto es el correo REAL (para clientes importados de Yuda
    # Contable, `email` es un usuario de portal sintético que no recibe
    # correo). Si nunca se guardó uno aparte, `email` es el respaldo -el
    # caso de los clientes creados a mano, donde sí es la casilla real.
    correo_real = destinatario.email_contacto or destinatario.email
    if not settings.BREVO_API_KEY or not settings.BREVO_SENDER_EMAIL:
        logger.warning("Brevo no está configurado; se omite el correo a %s", correo_real)
        return
    resp = httpx.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={
            "api-key": settings.BREVO_API_KEY,
            "content-type": "application/json",
            "accept": "application/json",
        },
        json={
            "sender": {"email": settings.BREVO_SENDER_EMAIL, "name": settings.BREVO_SENDER_NAME},
            "to": [{"email": correo_real, "name": destinatario.nombre}],
            "subject": asunto,
            "htmlContent": html,
        },
        timeout=10,
    )
    resp.raise_for_status()


def _lucidbot_headers() -> dict:
    return {"X-ACCESS-TOKEN": settings.LUCIDBOT_API_KEY}


def _normalizar_telefono(telefono: str) -> str:
    """Lucid Bot/ChatRace espera el teléfono con '+' y código de país
    (ej. '+573001234567'). Quita espacios/guiones y agrega el '+' si falta."""
    limpio = re.sub(r"[^\d+]", "", telefono)
    return limpio if limpio.startswith("+") else f"+{limpio}"


def _buscar_o_crear_contacto_lucidbot(cliente: Cliente) -> str | None:
    """Devuelve el contact_id interno de Lucid Bot para este teléfono,
    buscándolo primero y creándolo si no existe."""
    # whatsapp (de Yuda Contable) puede ser distinto del teléfono normal; si
    # no se guardó, se cae al teléfono, igual que antes.
    telefono = _normalizar_telefono(cliente.whatsapp or cliente.telefono or "")
    if not telefono or telefono == "+":
        logger.warning("Cliente %s no tiene teléfono; se omite el WhatsApp", cliente.email)
        return None

    def _buscar() -> list[dict]:
        r = httpx.get(
            f"{settings.LUCIDBOT_API_URL}/contacts/find_by_custom_field",
            headers=_lucidbot_headers(),
            params={"field_id": "phone", "value": telefono},
            timeout=10,
        )
        r.raise_for_status()
        return (r.json() or {}).get("data") or []

    encontrados = _buscar()
    if encontrados:
        return encontrados[0]["id"]

    nombre = (cliente.nombre or "").strip().split(" ", 1)
    resp = httpx.post(
        f"{settings.LUCIDBOT_API_URL}/contacts",
        headers=_lucidbot_headers(),
        json={
            "phone": telefono,
            "first_name": nombre[0] if nombre else cliente.nombre,
            "last_name": nombre[1] if len(nombre) > 1 else "",
            "email": cliente.email_contacto or cliente.email,
        },
        timeout=10,
    )
    resp.raise_for_status()
    creado = resp.json() if resp.content else {}
    if isinstance(creado, dict):
        contact_id = creado.get("id") or creado.get("data", {}).get("id")
        if contact_id:
            return contact_id

    # POST /contacts no documenta su body de respuesta; si no trae el id
    # directo, se vuelve a buscar por teléfono (ya debería existir).
    encontrados = _buscar()
    return encontrados[0]["id"] if encontrados else None


def _listar_custom_fields() -> dict[str, str]:
    """{nombre: id} de todos los custom fields de la cuenta de Lucid Bot."""
    resp = httpx.get(
        f"{settings.LUCIDBOT_API_URL}/accounts/custom_fields",
        headers=_lucidbot_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    campos = resp.json() or []
    return {c["name"]: c["id"] for c in campos if "name" in c and "id" in c}


def _establecer_custom_field(contact_id: str, custom_field_id: str, valor: str) -> None:
    resp = httpx.post(
        f"{settings.LUCIDBOT_API_URL}/contacts/{contact_id}/custom_fields/{custom_field_id}",
        headers=_lucidbot_headers(),
        data={"value": valor},
        timeout=10,
    )
    resp.raise_for_status()


def _disparar_flow(contact_id: str, flow_id: str) -> None:
    resp = httpx.post(
        f"{settings.LUCIDBOT_API_URL}/contacts/{contact_id}/send/{flow_id}",
        headers=_lucidbot_headers(),
        timeout=10,
    )
    resp.raise_for_status()


def _enviar_texto_libre(contact_id: str, texto: str) -> None:
    resp = httpx.post(
        f"{settings.LUCIDBOT_API_URL}/contacts/{contact_id}/send/text",
        headers={**_lucidbot_headers(), "content-type": "application/json"},
        json={"text": texto, "channel": "whatsapp"},
        timeout=10,
    )
    resp.raise_for_status()


def _enviar_whatsapp_lucidbot(
    cliente: Cliente, *, flow_id: str, campos_flow: dict[str, str], texto_libre: str
) -> None:
    """Envía un WhatsApp a través de Lucid Bot. `flow_id` y `campos_flow` son
    propios de cada tipo de aviso (aprobar despacho, pedido enviado, fecha
    tentativa, etc.): cada uno vive en su propio flow de Lucid Bot porque cada
    uno tiene su propia plantilla aprobada de WhatsApp. Si ese tipo de aviso no
    tiene flow configurado, se manda como texto libre (solo funciona dentro de
    la ventana de 24h desde el último mensaje del contacto al bot)."""
    if not settings.LUCIDBOT_API_KEY:
        logger.warning("LUCIDBOT_API_KEY no está configurada; se omite el WhatsApp a %s", cliente.email)
        return
    contact_id = _buscar_o_crear_contacto_lucidbot(cliente)
    if contact_id is None:
        return

    if not flow_id:
        # Modo texto libre: solo funciona dentro de la ventana de 24h.
        _enviar_texto_libre(contact_id, texto_libre)
        return

    # Modo plantilla: deja las variables en custom fields y dispara el flow
    # donde vive la plantilla de WhatsApp aprobada.
    ids_por_nombre = _listar_custom_fields()
    for nombre_campo, valor in campos_flow.items():
        custom_field_id = ids_por_nombre.get(nombre_campo)
        if custom_field_id is None:
            logger.warning(
                "Custom field '%s' no existe en Lucid Bot; esa variable no llega a la plantilla",
                nombre_campo,
            )
            continue
        _establecer_custom_field(contact_id, custom_field_id, valor)

    _disparar_flow(contact_id, flow_id)


def avisar_cliente_aprobar_despacho(
    db: Session, cliente: Cliente, sesion_id: str, numero: str, plazo: datetime, novedades: str | None = None
) -> None:
    """Bodega recibió e inspeccionó el pedido: el cliente tiene hasta `plazo`
    para aprobar el despacho desde su portal. Se avisa por correo y por
    WhatsApp; cada canal falla en silencio (solo queda en el log) para no
    tumbar el resto del guardado del seguimiento.

    `novedades` es la nota que bodega escribió al confirmar (el mismo texto
    que ya ve el cliente en el seguimiento del portal): si la dejó, se incluye
    en ambos avisos para que el cliente vea de una vez algo puntual (una caja
    faltante, etc.) sin tener que entrar al portal primero.
    """
    # Enlace mágico (no el link plano): a esta altura el cliente puede no
    # tener sesión abierta en el portal ni recordar su contraseña, y este es
    # un aviso automático -no hay quien la escriba a mano en el mensaje.
    link = _link_portal_magico(cliente.id, sesion_id, plazo)
    plazo_legible = _formatear_plazo(plazo)
    nota = (novedades or "").strip()

    try:
        nota_html = f"<p><strong>Nota de bodega:</strong> {nota}</p>" if nota else ""
        _enviar_correo_brevo(
            cliente,
            f"Tu pedido {numero} está listo para tu aprobación",
            f"""<p>Hola {cliente.nombre},</p>
<p>Bodega recibió e inspeccionó tu pedido <strong>{numero}</strong> y está listo para despacharse.
Ya puedes ver en tu portal las fotos que tomamos al revisarlo.</p>
{nota_html}
<p>Tienes hasta <strong>{plazo_legible}</strong> para revisarlo y aprobar el despacho desde tu portal.
Si no respondes antes de ese plazo, el despacho continúa de todas formas.</p>
<p><a href="{link}">Revisar y aprobar mi pedido</a></p>
<p>YUDA Importaciones</p>""",
        )
    except Exception as exc:
        logger.exception("No se pudo enviar el correo de aprobación de despacho a %s", cliente.email)
        _avisar_fallo(db, sesion_id, cliente, numero, "correo", exc)

    try:
        nota_wsp = f"\n\nNota de bodega: {nota}" if nota else ""
        texto_libre = (
            f"Hola {cliente.nombre}, bodega recibió e inspeccionó tu pedido {numero} y "
            f"está listo para despacharse. Ya puedes ver en tu portal las fotos que tomamos "
            f"al revisarlo.{nota_wsp}\n\nTienes hasta {plazo_legible} para "
            f"aprobar el despacho: {link}\nSi no respondes antes de ese plazo, el despacho "
            "continúa de todas formas."
        )
        _enviar_whatsapp_lucidbot(
            cliente,
            flow_id=settings.LUCIDBOT_FLOW_APROBAR_DESPACHO,
            campos_flow={
                settings.LUCIDBOT_CF_NUMERO_PEDIDO: numero,
                settings.LUCIDBOT_CF_PLAZO: plazo_legible,
                settings.LUCIDBOT_CF_LINK: link,
                settings.LUCIDBOT_CF_NOTA: nota,
            },
            texto_libre=texto_libre,
        )
    except Exception as exc:
        logger.exception("No se pudo enviar el WhatsApp de aprobación de despacho a %s", cliente.email)
        _avisar_fallo(db, sesion_id, cliente, numero, "WhatsApp", exc)


def avisar_cliente_cotizacion_enviada(db: Session, cliente: Cliente, sesion_id: str, numero: str) -> None:
    """Aviso simple: la vendedora acaba de enviarle una cotización nueva. Es
    lo primero que recibe el cliente, antes de que confirme nada. Correo y
    WhatsApp, cada uno best-effort."""
    link = _link_portal(sesion_id)

    try:
        _enviar_correo_brevo(
            cliente,
            f"Tienes una nueva cotización ({numero})",
            f"""<p>Hola {cliente.nombre},</p>
<p>Te enviamos una nueva cotización, <strong>{numero}</strong>. Puedes revisarla, pedir cambios
o confirmarla desde tu portal.</p>
<p><a href="{link}">Ver mi cotización</a></p>
<p>YUDA Importaciones</p>""",
        )
    except Exception as exc:
        logger.exception("No se pudo enviar el correo de 'cotización enviada' a %s", cliente.email)
        _avisar_fallo(db, sesion_id, cliente, numero, "correo", exc)

    try:
        texto_libre = (
            f"Hola {cliente.nombre}, te enviamos una nueva cotización ({numero}). "
            f"Puedes revisarla, pedir cambios o confirmarla desde tu portal.\n\nVerla: {link}"
        )
        _enviar_whatsapp_lucidbot(
            cliente,
            flow_id=settings.LUCIDBOT_FLOW_COTIZACION_ENVIADA,
            campos_flow={
                settings.LUCIDBOT_CF_NUMERO_PEDIDO: numero,
                settings.LUCIDBOT_CF_LINK: link,
            },
            texto_libre=texto_libre,
        )
    except Exception as exc:
        logger.exception("No se pudo enviar el WhatsApp de 'cotización enviada' a %s", cliente.email)
        _avisar_fallo(db, sesion_id, cliente, numero, "WhatsApp", exc)


def avisar_cliente_pedido_en_proveedor(db: Session, cliente: Cliente, sesion_id: str, numero: str) -> None:
    """Aviso simple: el pedido ya se mandó a comprar a los proveedores. Es el
    primer aviso externo que recibe el cliente después de confirmar sus
    cantidades, mucho antes de que bodega reciba nada. Correo y WhatsApp, cada
    uno best-effort."""
    link = _link_portal(sesion_id)

    try:
        _enviar_correo_brevo(
            cliente,
            f"Ya se pidió tu pedido {numero}",
            f"""<p>Hola {cliente.nombre},</p>
<p>Tu pedido <strong>{numero}</strong> ya se mandó a comprar a los proveedores. Apenas tengamos
una fecha estimada de cuándo va a estar listo te avisamos.</p>
<p><a href="{link}">Ver el estado de mi pedido</a></p>
<p>YUDA Importaciones</p>""",
        )
    except Exception as exc:
        logger.exception("No se pudo enviar el correo de 'pedido enviado a proveedor' a %s", cliente.email)
        _avisar_fallo(db, sesion_id, cliente, numero, "correo", exc)

    try:
        texto_libre = (
            f"Hola {cliente.nombre}, tu pedido {numero} ya se mandó a comprar a los "
            f"proveedores. Apenas tengamos fecha estimada te avisamos.\n\nVer el estado: {link}"
        )
        _enviar_whatsapp_lucidbot(
            cliente,
            flow_id=settings.LUCIDBOT_FLOW_PEDIDO_ENVIADO,
            campos_flow={
                settings.LUCIDBOT_CF_NUMERO_PEDIDO: numero,
                settings.LUCIDBOT_CF_LINK: link,
            },
            texto_libre=texto_libre,
        )
    except Exception as exc:
        logger.exception("No se pudo enviar el WhatsApp de 'pedido enviado a proveedor' a %s", cliente.email)
        _avisar_fallo(db, sesion_id, cliente, numero, "WhatsApp", exc)


def avisar_cliente_fecha_tentativa(
    db: Session, cliente: Cliente, sesion_id: str, numero: str, fecha_legible: str, supplier: str
) -> None:
    """Avisa al cliente la fecha aproximada que dio UN proveedor puntual para
    tener listo su pedido. Es por proveedor (no por cotización): si el
    pedido se reparte entre varios, cada uno manda su propio aviso, así que
    el nombre del proveedor va siempre en el mensaje para no confundir uno
    con otro. Correo y WhatsApp, cada uno best-effort."""
    link = _link_portal(sesion_id)

    try:
        _enviar_correo_brevo(
            cliente,
            f"Fecha estimada para tu pedido {numero}",
            f"""<p>Hola {cliente.nombre},</p>
<p>El proveedor «{supplier}» de tu pedido <strong>{numero}</strong> dijo que lo va a tener listo
aproximadamente el <strong>{fecha_legible}</strong>. Es una fecha estimada, puede variar.</p>
<p><a href="{link}">Ver el estado de mi pedido</a></p>
<p>YUDA Importaciones</p>""",
        )
    except Exception as exc:
        logger.exception("No se pudo enviar el correo de fecha tentativa a %s", cliente.email)
        _avisar_fallo(db, sesion_id, cliente, numero, "correo", exc)

    try:
        texto_libre = (
            f"Hola {cliente.nombre}, el proveedor «{supplier}» de tu pedido {numero} dijo que lo va a "
            f"tener listo aproximadamente el {fecha_legible} (fecha estimada, puede variar)."
            f"\n\nVer el estado: {link}"
        )
        _enviar_whatsapp_lucidbot(
            cliente,
            flow_id=settings.LUCIDBOT_FLOW_FECHA_TENTATIVA,
            campos_flow={
                settings.LUCIDBOT_CF_NUMERO_PEDIDO: numero,
                settings.LUCIDBOT_CF_LINK: link,
                settings.LUCIDBOT_CF_FECHA_TENTATIVA: fecha_legible,
            },
            texto_libre=texto_libre,
        )
    except Exception as exc:
        logger.exception("No se pudo enviar el WhatsApp de fecha tentativa a %s", cliente.email)
        _avisar_fallo(db, sesion_id, cliente, numero, "WhatsApp", exc)


def avisar_cliente_despachado(
    db: Session,
    cliente: Cliente,
    sesion_id: str,
    numero: str,
    naviera: str | None,
    numero_tracking: str | None,
    url_tracking: str | None,
    fecha_eta: date | None,
) -> None:
    """Avisa al cliente que su contenedor ya salió (etapa 'en_transito'), con
    la naviera y el tracking si Marcela ya los cargó. Correo y WhatsApp, cada
    uno best-effort."""
    link = _link_portal(sesion_id)
    eta_legible = formatear_fecha_legible(fecha_eta.isoformat()) if fecha_eta else None

    try:
        detalles = "".join(
            f"<p><strong>{etiqueta}:</strong> {valor}</p>"
            for etiqueta, valor in [
                ("Naviera", naviera),
                ("Tracking", numero_tracking),
                ("Llegada estimada", eta_legible),
            ]
            if valor
        )
        link_tracking = (
            f'<p><a href="{url_tracking}">Consultar el tracking</a></p>' if url_tracking else ""
        )
        _enviar_correo_brevo(
            cliente,
            f"Tu pedido {numero} ya está en camino",
            f"""<p>Hola {cliente.nombre},</p>
<p>Tu pedido <strong>{numero}</strong> ya salió: el contenedor está en tránsito.</p>
{detalles}
{link_tracking}
<p><a href="{link}">Ver el estado de mi pedido</a></p>
<p>YUDA Importaciones</p>""",
        )
    except Exception as exc:
        logger.exception("No se pudo enviar el correo de despacho a %s", cliente.email)
        _avisar_fallo(db, sesion_id, cliente, numero, "correo", exc)

    try:
        partes = [f"Hola {cliente.nombre}, tu pedido {numero} ya salió: el contenedor está en tránsito."]
        if naviera:
            partes.append(f"Naviera: {naviera}.")
        if numero_tracking:
            partes.append(f"Tracking: {numero_tracking}.")
        if eta_legible:
            partes.append(f"Llegada estimada: {eta_legible}.")
        partes.append(f"\n\nVer el estado: {link}")
        _enviar_whatsapp_lucidbot(
            cliente,
            flow_id=settings.LUCIDBOT_FLOW_DESPACHADO,
            campos_flow={
                settings.LUCIDBOT_CF_NUMERO_PEDIDO: numero,
                settings.LUCIDBOT_CF_LINK: link,
                settings.LUCIDBOT_CF_NAVIERA: naviera or "",
                settings.LUCIDBOT_CF_TRACKING: numero_tracking or "",
                settings.LUCIDBOT_CF_ETA: eta_legible or "",
            },
            texto_libre=" ".join(partes),
        )
    except Exception as exc:
        logger.exception("No se pudo enviar el WhatsApp de despacho a %s", cliente.email)
        _avisar_fallo(db, sesion_id, cliente, numero, "WhatsApp", exc)


def avisar_cliente_en_destino(db: Session, cliente: Cliente, sesion_id: str, numero: str) -> None:
    """Avisa al cliente que su contenedor llegó al país de destino, antes de
    la entrega final. Correo y WhatsApp, cada uno best-effort."""
    link = _link_portal(sesion_id)

    try:
        _enviar_correo_brevo(
            cliente,
            f"Tu pedido {numero} llegó a destino",
            f"""<p>Hola {cliente.nombre},</p>
<p>Tu pedido <strong>{numero}</strong> ya llegó al país de destino. En breve coordinamos la entrega.</p>
<p><a href="{link}">Ver el estado de mi pedido</a></p>
<p>YUDA Importaciones</p>""",
        )
    except Exception as exc:
        logger.exception("No se pudo enviar el correo de llegada a destino a %s", cliente.email)
        _avisar_fallo(db, sesion_id, cliente, numero, "correo", exc)

    try:
        texto_libre = (
            f"Hola {cliente.nombre}, tu pedido {numero} ya llegó al país de destino. "
            f"En breve coordinamos la entrega.\n\nVer el estado: {link}"
        )
        _enviar_whatsapp_lucidbot(
            cliente,
            flow_id=settings.LUCIDBOT_FLOW_EN_DESTINO,
            campos_flow={
                settings.LUCIDBOT_CF_NUMERO_PEDIDO: numero,
                settings.LUCIDBOT_CF_LINK: link,
            },
            texto_libre=texto_libre,
        )
    except Exception as exc:
        logger.exception("No se pudo enviar el WhatsApp de llegada a destino a %s", cliente.email)
        _avisar_fallo(db, sesion_id, cliente, numero, "WhatsApp", exc)


def avisar_cliente_entregado(db: Session, cliente: Cliente, sesion_id: str, numero: str) -> None:
    """Avisa al cliente que su pedido fue entregado. Correo y WhatsApp, cada
    uno best-effort."""
    link = _link_portal(sesion_id)

    try:
        _enviar_correo_brevo(
            cliente,
            f"Tu pedido {numero} fue entregado",
            f"""<p>Hola {cliente.nombre},</p>
<p>Tu pedido <strong>{numero}</strong> fue entregado. ¡Gracias por tu compra!</p>
<p><a href="{link}">Ver mi pedido</a></p>
<p>YUDA Importaciones</p>""",
        )
    except Exception as exc:
        logger.exception("No se pudo enviar el correo de entrega a %s", cliente.email)
        _avisar_fallo(db, sesion_id, cliente, numero, "correo", exc)

    try:
        texto_libre = (
            f"Hola {cliente.nombre}, tu pedido {numero} fue entregado. ¡Gracias por tu compra!"
            f"\n\nVer mi pedido: {link}"
        )
        _enviar_whatsapp_lucidbot(
            cliente,
            flow_id=settings.LUCIDBOT_FLOW_ENTREGADO,
            campos_flow={
                settings.LUCIDBOT_CF_NUMERO_PEDIDO: numero,
                settings.LUCIDBOT_CF_LINK: link,
            },
            texto_libre=texto_libre,
        )
    except Exception as exc:
        logger.exception("No se pudo enviar el WhatsApp de entrega a %s", cliente.email)
        _avisar_fallo(db, sesion_id, cliente, numero, "WhatsApp", exc)
