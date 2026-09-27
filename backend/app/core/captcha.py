import os

import httpx

_HCAPTCHA_VERIFY_URL = "https://hcaptcha.com/siteverify"


def captcha_requerido() -> bool:
    """En local/tests no hay secret key configurada: no se exige captcha."""
    return bool(os.environ.get("HCAPTCHA_SECRET_KEY"))


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
