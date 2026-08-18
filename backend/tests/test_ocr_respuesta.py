"""Lectura de la respuesta del modelo de visión.

Con el pensamiento prendido (Opus 5 lo trae por defecto) la respuesta llega con
bloques "thinking" ANTES del texto, así que no se puede asumir que el JSON está en
content[0]. Y si el tope de tokens se queda corto, la respuesta viene sin texto:
eso tiene que dar resultado vacío, no reventar.
"""
import asyncio
import json

import app.services.ocr_service as ocr

DATOS = {
    "descripcion_es": "Vaso plástico con tapa",
    "price_rmb": 8.5,
    "qty_por_ctn": 240,
    "confianza": "alta",
    "legible": True,
    "motivo_ilegible": None,
}


class _Bloque:
    def __init__(self, tipo: str, texto: str = "", pensamiento: str = ""):
        self.type = tipo
        self.text = texto
        self.thinking = pensamiento


class _Respuesta:
    def __init__(self, bloques, stop_reason="end_turn"):
        self.content = bloques
        self.stop_reason = stop_reason


class _ClienteFalso:
    """Sustituye al cliente de Anthropic: guarda con qué se llamó y responde fijo."""

    def __init__(self, respuesta):
        self._respuesta = respuesta
        self.llamada = {}
        self.messages = self

    async def create(self, **kwargs):
        self.llamada.update(kwargs)
        return self._respuesta


def _correr(monkeypatch, respuesta):
    cliente = _ClienteFalso(respuesta)
    monkeypatch.setattr(ocr, "_get_client", lambda: cliente)
    datos = asyncio.run(ocr.extraer_datos_etiqueta(b"\xff\xd8\xff", "image/jpeg"))
    return datos, cliente


def test_lee_el_json_aunque_venga_despues_del_pensamiento(monkeypatch):
    respuesta = _Respuesta([
        _Bloque("thinking", pensamiento="El cartel dice 单价 8.5 y 每箱 240..."),
        _Bloque("text", texto=json.dumps(DATOS)),
    ])
    datos, _ = _correr(monkeypatch, respuesta)
    assert datos["descripcion_es"] == "Vaso plástico con tapa"
    assert datos["price_rmb"] == 8.5
    assert datos["qty_por_ctn"] == 240
    assert datos["legible"] is True


def test_sin_bloque_de_texto_devuelve_resultado_vacio(monkeypatch):
    # Pasa si el tope de tokens se agota pensando: no hay JSON que leer.
    respuesta = _Respuesta([_Bloque("thinking", pensamiento="...")], stop_reason="max_tokens")
    datos, _ = _correr(monkeypatch, respuesta)
    assert datos["legible"] is False
    assert datos["motivo_ilegible"] == "no_procesada"
    assert datos["price_rmb"] is None


def test_llama_al_modelo_con_el_esfuerzo_y_el_tope_configurados(monkeypatch):
    respuesta = _Respuesta([_Bloque("text", texto=json.dumps(DATOS))])
    _, cliente = _correr(monkeypatch, respuesta)
    assert cliente.llamada["model"] == ocr.MODELO
    assert cliente.llamada["output_config"] == {"effort": ocr.ESFUERZO}
    # El tope incluye el pensamiento; con 1024 la respuesta se cortaba a la mitad.
    assert cliente.llamada["max_tokens"] == ocr.MAX_TOKENS > 1024


def test_error_de_la_api_no_propaga(monkeypatch):
    class _ClienteQueFalla:
        def __init__(self):
            self.messages = self

        async def create(self, **kwargs):
            raise RuntimeError("API caída")

    monkeypatch.setattr(ocr, "_get_client", lambda: _ClienteQueFalla())
    datos = asyncio.run(ocr.extraer_datos_etiqueta(b"\xff\xd8\xff", "image/jpeg"))
    assert datos["legible"] is False
    assert datos["confianza"] == "baja"
