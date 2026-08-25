"""Un fallo NUESTRO (API caída, sin crédito, respuesta ilegible) no puede presentarse
como "la foto no se lee".

El 15-ago-2026 la cuenta de Anthropic se quedó sin saldo a media mañana. El OCR
guardaba el resultado vacío con motivo "no_procesada", la app mostraba «Foto no
legible — vuelve a tomarla», y una vendedora refotografió y reintentó tres veces:
268 fotos, ninguna con datos, y terminó escribiendo 73 productos a mano.
"""
import asyncio
import json

import app.services.ocr_service as ocr
from app.services.ocr_service import MOTIVO_ERROR_SISTEMA, es_error_sistema


class _Bloque:
    def __init__(self, tipo, texto=""):
        self.type = tipo
        self.text = texto


class _Respuesta:
    def __init__(self, bloques, stop_reason="end_turn"):
        self.content = bloques
        self.stop_reason = stop_reason


def _correr(monkeypatch, respuesta=None, excepcion=None):
    class _Cliente:
        def __init__(self):
            self.messages = self

        async def create(self, **kw):
            if excepcion:
                raise excepcion
            return respuesta

    monkeypatch.setattr(ocr, "_get_client", lambda: _Cliente())
    return asyncio.run(ocr.extraer_datos_etiqueta(b"\xff\xd8\xff", "image/jpeg"))


def test_sin_credito_se_reporta_como_falta_de_saldo(monkeypatch):
    # Lo que devolvió la API el 15-ago: 400 "credit balance is too low". La vendedora
    # tiene que ver "la cuenta se quedó sin saldo", no un "error del sistema" que
    # manda a buscar un bug inexistente.
    d = _correr(monkeypatch, excepcion=RuntimeError("credit balance is too low"))
    assert d["motivo_ilegible"] == ocr.MOTIVO_SIN_SALDO
    assert es_error_sistema(d)          # sigue siendo culpa nuestra, no de la foto


def test_respuesta_sin_texto_es_error_del_sistema(monkeypatch):
    d = _correr(monkeypatch, _Respuesta([_Bloque("thinking")], stop_reason="max_tokens"))
    assert es_error_sistema(d)


def test_respuesta_que_no_es_json_es_error_del_sistema(monkeypatch):
    d = _correr(monkeypatch, _Respuesta([_Bloque("text", "perdón, no puedo ayudarte")]))
    assert es_error_sistema(d)


def test_una_foto_borrosa_NO_es_error_del_sistema(monkeypatch):
    # Acá el modelo sí respondió y dijo que la foto no se lee: eso sí se le muestra
    # a la vendedora como "vuelve a tomarla", porque tiene algo que corregir.
    borrosa = {"descripcion_es": None, "price_rmb": None, "confianza": "baja",
               "legible": False, "motivo_ilegible": "borrosa"}
    d = _correr(monkeypatch, _Respuesta([_Bloque("text", json.dumps(borrosa))]))
    assert d["motivo_ilegible"] == "borrosa"
    assert not es_error_sistema(d)


def test_una_foto_buena_no_marca_nada(monkeypatch):
    ok = {"descripcion_es": "Vaso", "price_rmb": 8.5, "confianza": "alta",
          "legible": True, "motivo_ilegible": None}
    d = _correr(monkeypatch, _Respuesta([_Bloque("text", json.dumps(ok))]))
    assert d["legible"] is True
    assert not es_error_sistema(d)


def test_es_error_sistema_tolera_vacios():
    assert not es_error_sistema(None)
    assert not es_error_sistema({})


def test_otro_fallo_de_api_queda_como_error_generico(monkeypatch):
    d = _correr(monkeypatch, excepcion=RuntimeError("connection reset by peer"))
    assert d["motivo_ilegible"] == MOTIVO_ERROR_SISTEMA
    assert es_error_sistema(d)
