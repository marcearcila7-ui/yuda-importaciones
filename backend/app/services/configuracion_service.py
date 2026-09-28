from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.configuracion import Configuracion

CLAVE_TIPO_CAMBIO = "tipo_cambio_usd"


def obtener_tipo_cambio_actual(db: Session) -> float:
    """Tipo de cambio vigente, configurado por Marcela desde Admin >
    Configuración. Es el único origen válido: ningún endpoint debe confiar en
    un tipo_cambio_usd que venga en el cuerpo de la petición, porque eso le
    permitiría a una vendedora cotizar con una tasa distinta a la oficial."""
    registro = db.query(Configuracion).filter(Configuracion.clave == CLAVE_TIPO_CAMBIO).first()
    if registro is None:
        return settings.TIPO_CAMBIO_USD
    return float(registro.valor)
