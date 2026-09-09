"""Envío de correos (por ahora, solo el de recuperar contraseña).

Usa smtplib de la librería estándar en vez de sumar una dependencia nueva:
el volumen es bajo (recuperaciones de contraseña de un equipo chico), así
que no hace falta un servicio de correo transaccional aparte.
"""
import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def _enviar_smtp(destinatario: str, asunto: str, texto: str, html: str) -> None:
    mensaje = MIMEMultipart("alternative")
    mensaje["Subject"] = asunto
    mensaje["From"] = settings.smtp_from_efectivo
    mensaje["To"] = destinatario
    mensaje.attach(MIMEText(texto, "plain"))
    mensaje.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        smtp.starttls()
        smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(mensaje)


async def enviar_recuperacion(destinatario: str, nombre: str, link: str) -> None:
    """Manda el correo con el enlace para elegir una contraseña nueva.

    Sin SMTP_HOST configurado (típico en desarrollo) no falla: solo deja el
    enlace en los logs, para poder probar el flujo sin credenciales reales.
    """
    asunto = "Recuperar tu contraseña — YUDA Importaciones"
    texto = (
        f"Hola {nombre},\n\n"
        f"Pediste recuperar tu contraseña de YUDA Importaciones. Entra a este "
        f"enlace para elegir una nueva (vence en 1 hora):\n\n{link}\n\n"
        f"Si no fuiste tú, ignora este correo: tu contraseña actual sigue igual."
    )
    html = (
        f"<p>Hola {nombre},</p>"
        f"<p>Pediste recuperar tu contraseña de <strong>YUDA Importaciones</strong>. "
        f'Toca el botón para elegir una nueva (vence en 1 hora):</p>'
        f'<p><a href="{link}" style="background:#0E6B66;color:#fff;padding:10px 20px;'
        f'border-radius:8px;text-decoration:none;display:inline-block">Elegir nueva contraseña</a></p>'
        f'<p style="color:#666;font-size:13px">Si no fuiste tú, ignora este correo: '
        f"tu contraseña actual sigue igual.</p>"
    )

    if not settings.SMTP_HOST:
        logger.info("SMTP_HOST no configurado; enlace de recuperación para %s: %s", destinatario, link)
        return

    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, lambda: _enviar_smtp(destinatario, asunto, texto, html))
    except Exception:
        # No se relanza: si el correo falla, el token ya quedó guardado y el
        # endpoint igual responde el mensaje genérico (no hay que filtrar por qué).
        logger.exception("No se pudo enviar el correo de recuperación a %s", destinatario)
