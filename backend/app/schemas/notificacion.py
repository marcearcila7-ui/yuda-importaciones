from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificacionResponse(BaseModel):
    """Aviso interno para un usuario del equipo"""

    id: str
    sesion_id: str | None = None
    tipo: str
    titulo: str
    mensaje: str | None = None
    leida: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
