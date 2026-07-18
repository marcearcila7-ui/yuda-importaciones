"""Cabeceras de seguridad HTTP para todas las respuestas.

YUDA es una API JSON que además sirve imágenes bajo /uploads; estas cabeceras
endurecen el navegador sin romper ese uso:

- Strict-Transport-Security: fuerza HTTPS (Railway ya sirve por HTTPS) y evita el
  downgrade a HTTP en visitas futuras.
- X-Content-Type-Options: nosniff -> el navegador no "adivina" tipos de contenido.
- X-Frame-Options / frame-ancestors: nadie puede embeber la app en un <iframe>
  (protección contra clickjacking).
- Referrer-Policy: no filtra la URL completa a terceros.
- Content-Security-Policy: base conservadora que permite las imágenes propias de
  /uploads (self + data:) y prohíbe el framing.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for nombre, valor in _HEADERS.items():
            response.headers.setdefault(nombre, valor)
        return response
