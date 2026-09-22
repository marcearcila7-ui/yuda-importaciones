import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base

# Tipos de entrada en el hilo de cubicaje de un pedido.
TIPO_REPORTE = "reporte"       # bodega manda el cálculo de cubicaje (sobra/falta/ajustado)
TIPO_NOTA = "nota"             # nota libre de bodega, sin recalcular nada
TIPO_RESPUESTA = "respuesta"   # respuesta de la vendedora a un reporte o nota

# Resultado del cálculo frente al rango de contenedor (68-72 m3, ver
# cubicaje_service.py). Solo se llena en tipo="reporte".
RESULTADO_SOBRA = "sobra"       # el pedido completo no cabe: hay que dejar cajas afuera
RESULTADO_FALTA = "falta"       # no se alcanza el mínimo, queda espacio libre
RESULTADO_AJUSTADO = "ajustado"  # cae dentro del rango 68-72, sin sobrantes ni faltantes


class CubicajeMensaje(Base):
    """Hilo de cubicaje de un pedido: reportes de bodega (cuánto cubicaje
    calculó el sistema, y si sobra o falta espacio frente al rango de un
    contenedor) más la conversación alrededor -notas de bodega, respuestas de
    la vendedora. Todo en el orden en que pasó, con fecha y hora, para que
    ambas partes vean el mismo control."""

    __tablename__ = "cubicaje_mensajes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sesion_id: Mapped[str] = mapped_column(
        String, ForeignKey("sesiones.id"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    autor_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)

    mensaje: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Solo se llenan en tipo="reporte": lo que el sistema calculó en ese
    # momento (nunca lo escribe el usuario, evita que quede desactualizado).
    cbm_calculado: Mapped[float | None] = mapped_column(Float, nullable=True)
    resultado: Mapped[str | None] = mapped_column(String, nullable=True)
    # Si resultado="sobra": qué referencia y cuántas cajas quedaron afuera
    # (bodega las elige de las referencias reales del pedido).
    referencia: Mapped[str | None] = mapped_column(String, nullable=True)
    cajas_afectadas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Si resultado="falta": cuánto espacio (m3) queda libre.
    espacio_restante_cbm: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
