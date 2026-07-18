from app.core import rate_limit as rl


def setup_function():
    rl._intentos.clear()


def test_bloquea_tras_el_limite():
    for _ in range(5):
        assert not rl.esta_bloqueado("k", 5, 900)
        rl.registrar_fallo("k", 900)
    assert rl.esta_bloqueado("k", 5, 900)


def test_limpiar_resetea_el_contador():
    for _ in range(5):
        rl.registrar_fallo("k", 900)
    assert rl.esta_bloqueado("k", 5, 900)
    rl.limpiar("k")
    assert not rl.esta_bloqueado("k", 5, 900)


def test_claves_independientes():
    for _ in range(5):
        rl.registrar_fallo("a", 900)
    assert rl.esta_bloqueado("a", 5, 900)
    assert not rl.esta_bloqueado("b", 5, 900)


def test_ventana_cero_no_bloquea():
    # Con ventana 0, todo intento queda fuera de la ventana al chequear.
    for _ in range(10):
        rl.registrar_fallo("k", 0)
    assert not rl.esta_bloqueado("k", 5, 0)
