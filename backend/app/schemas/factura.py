from pydantic import BaseModel


class FacturaRequest(BaseModel):
    """Solicitud de generación de factura en USD.

    Si se envía `contenedor_id`, se vincula la cotización a ese contenedor y se
    usa su TRM. Si se omite, se usa el contenedor ya vinculado a la cotización o,
    en su defecto, `sesion.tipo_cambio_usd`.
    """

    contenedor_id: str | None = None
    # De (FROM) y Para (TO) editables por el usuario antes de generar la factura.
    de: str | None = None
    para: str | None = None
