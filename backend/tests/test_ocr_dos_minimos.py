"""Los carteles de Yiwu suelen traer DOS mínimos: uno por modelo ("MOQ: 2 cajas por
modelo") y otro por tienda ("toda tienda: 10 cajas"). El OCR devuelve los dos y la
app le muestra a la vendedora cuál está usando, con un toque para cambiar.

Estos tests cubren la parte mecánica (que el campo exista, se convierta a número y no
se duplique). Lo que NO se puede probar acá es si el modelo separa bien los dos
mínimos leyendo un cartel real: eso solo se ve con el uso.
"""
import asyncio
import json

import app.services.ocr_service as ocr

BASE = {"descripcion_es": "Pelota de goma", "confianza": "alta", "legible": True,
        "motivo_ilegible": None}


class _Bloque:
    def __init__(self, texto):
        self.type = "text"
        self.text = texto


class _Respuesta:
    def __init__(self, datos):
        self.content = [_Bloque(json.dumps(datos))]
        self.stop_reason = "end_turn"


def _correr(monkeypatch, datos):
    class _Cliente:
        def __init__(self): self.messages = self
        async def create(self, **kw): return _Respuesta(datos)

    monkeypatch.setattr(ocr, "_get_client", lambda: _Cliente())
    return asyncio.run(ocr.extraer_datos_etiqueta(b"\xff\xd8\xff", "image/jpeg"))


def test_devuelve_los_dos_minimos(monkeypatch):
    d = _correr(monkeypatch, {**BASE, "cantidad_minima": 2, "cantidad_minima_tienda": 10})
    assert d["cantidad_minima"] == 2
    assert d["cantidad_minima_tienda"] == 10


def test_un_solo_minimo_deja_el_de_tienda_vacio(monkeypatch):
    d = _correr(monkeypatch, {**BASE, "cantidad_minima": 600})
    assert d["cantidad_minima"] == 600
    assert d["cantidad_minima_tienda"] is None


def test_el_mismo_numero_en_los_dos_no_genera_aviso(monkeypatch):
    # Si el modelo repite el número, la app mostraría un aviso de "hay dos mínimos"
    # que en realidad es uno solo: se descarta el duplicado.
    d = _correr(monkeypatch, {**BASE, "cantidad_minima": 10, "cantidad_minima_tienda": 10})
    assert d["cantidad_minima"] == 10
    assert d["cantidad_minima_tienda"] is None


def test_convierte_a_entero(monkeypatch):
    d = _correr(monkeypatch, {**BASE, "cantidad_minima": "2 cajas", "cantidad_minima_tienda": "十"})
    assert d["cantidad_minima"] == 2
    assert d["cantidad_minima_tienda"] == 10        # numeral chino
    assert isinstance(d["cantidad_minima_tienda"], int)


def test_una_foto_vieja_sin_el_campo_no_rompe(monkeypatch):
    d = _correr(monkeypatch, {**BASE, "cantidad_minima": 5})
    assert "cantidad_minima_tienda" in d and d["cantidad_minima_tienda"] is None


# El prompt es lo que hace que el modelo separe los dos mínimos; si alguien recorta
# estas reglas, el OCR vuelve a devolver uno solo y nadie se entera hasta produccion.
def test_el_prompt_explica_los_dos_minimos():
    assert "cantidad_minima_tienda" in ocr.PROMPT
    for pista in ("por modelo", "toda tienda", "每款", "全店", "per model"):
        assert pista in ocr.PROMPT
    assert "NUNCA repitas el mismo número en los dos campos" in ocr.PROMPT
