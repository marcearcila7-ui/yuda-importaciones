"""Limitador de intentos de login en memoria (anti fuerza bruta).

Ventana deslizante por clave (email o IP). Suficiente para un servicio de un solo
proceso como este; si el proceso reinicia, los contadores se reinician (aceptable).
No usa dependencias externas ni base de datos.
"""
import threading
import time

_intentos: dict[str, list[float]] = {}
_lock = threading.Lock()


def _podar(sellos: list[float], ventana_seg: int, ahora: float) -> list[float]:
    """Deja solo los intentos dentro de la ventana."""
    return [t for t in sellos if ahora - t < ventana_seg]


def esta_bloqueado(clave: str, limite: int, ventana_seg: int) -> bool:
    """True si `clave` acumuló >= `limite` intentos fallidos en la ventana."""
    ahora = time.monotonic()
    with _lock:
        sellos = _podar(_intentos.get(clave, []), ventana_seg, ahora)
        if sellos:
            _intentos[clave] = sellos
        else:
            _intentos.pop(clave, None)
        return len(sellos) >= limite


def registrar_fallo(clave: str, ventana_seg: int) -> None:
    """Registra un intento fallido para `clave`."""
    ahora = time.monotonic()
    with _lock:
        sellos = _podar(_intentos.get(clave, []), ventana_seg, ahora)
        sellos.append(ahora)
        _intentos[clave] = sellos


def limpiar(clave: str) -> None:
    """Borra los intentos de `clave` (tras un login exitoso)."""
    with _lock:
        _intentos.pop(clave, None)


def ip_del_request(request) -> str:
    """IP real del cliente, respetando el proxy de Railway (X-Forwarded-For)."""
    reenviada = request.headers.get("x-forwarded-for")
    if reenviada:
        return reenviada.split(",")[0].strip()
    return request.client.host if request.client else "desconocida"
