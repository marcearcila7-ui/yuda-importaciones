import uuid
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base

# Hitos del envío en orden, pensados para una agencia de importación China → destino.
# El cliente ve esta línea de tiempo en su portal.
ESTADOS_ENVIO = [
    "cotizacion_enviada",   # La vendedora envió la cotización al cliente
    "pedido_confirmado",    # El cliente confirmó el pedido
    "proveedor_recibio",    # El proveedor recibió el pedido
    "en_bodega",            # Mercancía recibida en bodega (lista para envío)
    "en_transito",          # En tránsito: contenedores en camino (tracking + naviera)
    "en_destino",           # Arribó al país de destino
    "entregado",            # Entregado al cliente
]

ESTADO_INICIAL = "cotizacion_enviada"

# Etapas que la vendedora puede gestionar. "en_bodega" en adelante es
# exclusivo de bodega (recepción física) y Marcela (admin): antes estaba acá
# por error y una vendedora podía marcar "en bodega" ella misma desde su
# propio desplegable, saltándose por completo la revisión de bodega y sin que
# nunca se le abriera al cliente el plazo para aprobar el despacho (quedaba
# atascado para siempre, sin forma de llegar a "en tránsito").
ESTADOS_VENDEDORA = [
    "cotizacion_enviada",
    "pedido_confirmado",
    "proveedor_recibio",
]

# Campos de envío que solo Marcela (admin) puede editar.
CAMPOS_SOLO_ADMIN = ("numero_tracking", "naviera", "url_tracking", "bl_numero", "bl_pdf_url")

# Etapa que dispara el aviso a Marcela: la mercancía está lista para enviarse,
# es el momento de cargar naviera y BL.
ESTADO_DISPARA_AVISO = "en_bodega"


class SeguimientoPedido(Base):
    """Seguimiento del envío de una cotización (1 a 1 con la sesión)."""

    __tablename__ = "seguimientos"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sesion_id: Mapped[str] = mapped_column(
        String, ForeignKey("sesiones.id"), unique=True, nullable=False
    )
    estado: Mapped[str] = mapped_column(String, default=ESTADO_INICIAL, nullable=False)
    # Mensaje que la vendedora/Marcela le deja al cliente manualmente en el
    # editor de Seguimiento (cualquier etapa). Campo aparte de
    # nota_bodega_aprobacion: antes compartían la misma columna y bodega, al
    # marcar "en_bodega", pisaba sin querer lo que Marcela veía acá -parecía
    # que había aparecido de la nada un texto que nadie del equipo interno
    # reconocía haber escrito.
    novedades: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Mensaje que BODEGA le deja al cliente específicamente al marcar
    # "en_bodega" (enviar a aprobación del despacho): se le muestra en su
    # portal y va por correo en ese momento. Independiente de `novedades`.
    nota_bodega_aprobacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    numero_tracking: Mapped[str | None] = mapped_column(String, nullable=True)
    naviera: Mapped[str | None] = mapped_column(String, nullable=True)
    url_tracking: Mapped[str | None] = mapped_column(String, nullable=True)
    fecha_eta: Mapped[date | None] = mapped_column(Date, nullable=True)
    # BL (Bill of Lading): lo carga Marcela cuando el contenedor está en tránsito.
    bl_numero: Mapped[str | None] = mapped_column(String, nullable=True)
    bl_pdf_url: Mapped[str | None] = mapped_column(String, nullable=True)
    # Monto de la venta en USD, que Marcela ingresa al despachar (obligatorio al
    # pasar a "en tránsito"). Alimenta el panel de ventas del dashboard.
    monto_venta: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    # Sello de cuándo el pedido pasó a "en tránsito" (despacho del contenedor),
    # para filtrar las ventas por fecha en el panel de Marcela.
    despachado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    # { estado_key: { "fecha": "YYYY-MM-DD", "nota": "..." } }
    hitos: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Avisos automáticos al cliente que NO son un cambio de etapa (ej. la
    # fecha tentativa de una tienda puntual): a diferencia de `hitos`, esta
    # columna solo se anexa, nunca se reconstruye desde cero, para que la
    # vendedora vea en el historial cada notificación real que salió sola.
    # [{ "tipo": "...", "detalle": "...", "ts": "2026-09-25T..." }]
    avisos: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # El cliente aprueba, desde su portal, el despacho una vez bodega recibió e
    # inspeccionó la mercancía ("en_bodega"). Sin esta aprobación (o sin que
    # venza el plazo de abajo) Marcela no puede pasar el pedido a "en_transito".
    cliente_aprobo_despacho_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Plazo que bodega le da al cliente para aprobar (lo fija al marcar
    # "en_bodega"). Si se vence sin aprobación, el despacho sigue de todas
    # formas: el cliente ya no puede aprobar ni objetar pasado este momento.
    aprobacion_limite_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Con varias personas en bodega, este pedido puede estar sin repartir (None)
    # o en manos de alguien puntual. None no significa "nadie lo puede ver": lo
    # ven todos, solo que nadie lo tomó todavía.
    bodega_asignado_a_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id"), nullable=True
    )
    bodega_asignado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bodega_asignado_por_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id"), nullable=True
    )
    # Bodega puede sacar un pedido de su propia cola (ej. ya está completado
    # hace rato) sin borrar nada del sistema: solo deja de aparecer en sus 4
    # pestañas, para que la lista no se llene de trabajo ya resuelto.
    bodega_archivado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def registrar_aviso(seg: SeguimientoPedido, tipo: str, detalle: str) -> None:
    """Anota en `avisos` que un aviso automático salió, con su fecha y hora
    reales. Se reasigna una lista nueva (no se muta la existente) para que
    SQLAlchemy detecte el cambio en una columna JSON."""
    ahora = datetime.now(timezone.utc).isoformat()
    seg.avisos = [*(seg.avisos or []), {"tipo": tipo, "detalle": detalle, "ts": ahora}]
