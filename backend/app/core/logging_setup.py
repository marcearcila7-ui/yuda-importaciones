"""Configuración central de logging. Reemplaza los print() sueltos por logging
con nivel y timestamp, escrito a stdout (Railway/Docker lo capturan)."""
import logging

_configurado = False


def configurar_logging() -> None:
    """Configura el logging raíz una sola vez (idempotente). Nivel vía LOG_LEVEL."""
    global _configurado
    if _configurado:
        return
    from app.core.config import settings

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    _configurado = True
