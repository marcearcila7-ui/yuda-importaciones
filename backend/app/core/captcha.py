import os

import httpx

_HCAPTCHA_VERIFY_URL = "https://hcaptcha.com/siteverify"


def captcha_requerido(origin: str | None = None) -> bool:
    """En local/tests no hay secret key configurada: no se exige captcha.

    Yuda Calendario es de uso interno (mismo staff que ya tiene cuenta, sin
    formulario público), así que sus orígenes quedan exentos del captcha que
    sí protege los formularios públicos (cotizador, portal de clientes).
    """
    if not os.environ.get("HCAPTCHA_SECRET_KEY"):
        return False
    exentos = {o.strip() for o in os.environ.get("CAPTCHA_EXENTO_ORIGINS", "").split(",") if o.strip()}
    return origin not in exentos


def verificar_captcha(token: str | None) -> bool:
    """Valida el token de hCaptcha contra la API oficial.

    Si no hay HCAPTCHA_SECRET_KEY configurada (desarrollo local, tests), no
    se exige captcha y esta función no se llama (ver captcha_requerido()).
    """
    secret = os.environ.get("HCAPTCHA_SECRET_KEY")
    if not secret:
        return True
    if not token:
        return False
    try:
        respuesta = httpx.post(
            _HCAPTCHA_VERIFY_URL,
            data={"secret": secret, "response": token},
            timeout=10,
        )
        return bool(respuesta.json().get("success"))
    except httpx.HTTPError:
        # Si hCaptcha no responde, no dejamos a nadie afuera del sistema
        # por una falla ajena: se deja pasar (igual que si no fuera exigido).
        return True
