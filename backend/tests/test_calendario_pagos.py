"""Calendario de pagos (área contable): crear/editar un pago debe validar que
el cliente exista y guardar su sigla; editar (incluido "mover" de día) debe
dejar registrado quién lo editó por última vez; eliminar debe funcionar sin
error; y solo admin/contadora tienen acceso (ni vendedora ni bodega)."""
from app.models.user import RolUsuario


def test_crear_pago_valida_cliente_y_guarda_sigla(db, client, crear_usuario, crear_cliente, token_staff):
    admin = crear_usuario("pg-admin1@test.com", rol=RolUsuario.admin, nombre="Marcela")
    contadora = crear_usuario("pg-c1@test.com", rol=RolUsuario.contadora, nombre="Contadora Uno")
    cliente = crear_cliente("pg-cliente1@test.com", vendedora_id=admin.id, nombre="Cliente Uno")
    cliente.sigla = "ABC"
    db.commit()

    tok = token_staff("pg-c1@test.com")
    r = client.post(
        "/api/v1/calendario-pagos/pagos",
        json={"fecha": "2026-10-10", "tienda": "Tienda Yiwu 1", "cliente_id": cliente.id, "monto": "1500.50", "estatus": "no_pagado"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["cliente_sigla"] == "ABC"
    assert data["creado_por_nombre"] == "Contadora Uno"
    assert data["estatus"] == "no_pagado"
    assert data["actualizado_por_id"] is None


def test_crear_pago_con_cliente_inexistente_da_404(client, crear_usuario, token_staff):
    crear_usuario("pg-c2@test.com", rol=RolUsuario.contadora, nombre="Contadora Dos")
    tok = token_staff("pg-c2@test.com")
    r = client.post(
        "/api/v1/calendario-pagos/pagos",
        json={"fecha": "2026-10-10", "tienda": "Tienda X", "cliente_id": "no-existe", "monto": "100", "estatus": "no_pagado"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 404


def test_editar_pago_mueve_de_dia_y_registra_quien_edito(db, client, crear_usuario, crear_cliente, token_staff):
    admin = crear_usuario("pg-admin2@test.com", rol=RolUsuario.admin, nombre="Marcela")
    contadora = crear_usuario("pg-c3@test.com", rol=RolUsuario.contadora, nombre="Contadora Tres")
    cliente = crear_cliente("pg-cliente2@test.com", vendedora_id=admin.id, nombre="Cliente Dos")
    cliente.sigla = "XYZ"
    db.commit()

    tok = token_staff("pg-c3@test.com")
    r = client.post(
        "/api/v1/calendario-pagos/pagos",
        json={"fecha": "2026-10-05", "tienda": "Tienda Yiwu 2", "cliente_id": cliente.id, "monto": "800", "estatus": "no_pagado"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    pago_id = r.json()["id"]

    # "Mover" el pago al arrastrarlo es, para el backend, editar la fecha.
    r2 = client.put(
        f"/api/v1/calendario-pagos/pagos/{pago_id}",
        json={"fecha": "2026-10-12", "tienda": "Tienda Yiwu 2", "cliente_id": cliente.id, "monto": "800", "estatus": "pagado"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert data["fecha"] == "2026-10-12"
    assert data["estatus"] == "pagado"
    assert data["actualizado_por_nombre"] == "Contadora Tres"
    assert data["actualizado_en"] is not None
    assert data["creado_por_nombre"] == "Contadora Tres"


def test_eliminar_pago(client, crear_usuario, crear_cliente, token_staff):
    admin = crear_usuario("pg-admin3@test.com", rol=RolUsuario.admin, nombre="Marcela")
    crear_usuario("pg-c4@test.com", rol=RolUsuario.contadora, nombre="Contadora Cuatro")
    cliente = crear_cliente("pg-cliente3@test.com", vendedora_id=admin.id, nombre="Cliente Tres")

    tok = token_staff("pg-c4@test.com")
    r = client.post(
        "/api/v1/calendario-pagos/pagos",
        json={"fecha": "2026-10-08", "tienda": "Tienda Yiwu 3", "cliente_id": cliente.id, "monto": "200", "estatus": "aplazado"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    pago_id = r.json()["id"]

    r2 = client.delete(f"/api/v1/calendario-pagos/pagos/{pago_id}", headers={"Authorization": f"Bearer {tok}"})
    assert r2.status_code == 200, r2.text

    r3 = client.get(
        "/api/v1/calendario-pagos/pagos",
        params={"desde": "2026-10-01", "hasta": "2026-10-31"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert pago_id not in {p["id"] for p in r3.json()}


def test_vendedora_y_bodega_no_tienen_acceso(client, crear_usuario, token_staff):
    crear_usuario("pg-v1@test.com", rol=RolUsuario.vendedora, nombre="Vendedora")
    crear_usuario("pg-b1@test.com", rol=RolUsuario.bodega, nombre="Bodega")
    for email in ("pg-v1@test.com", "pg-b1@test.com"):
        tok = token_staff(email)
        r = client.get(
            "/api/v1/calendario-pagos/pagos",
            params={"desde": "2026-10-01", "hasta": "2026-10-31"},
            headers={"Authorization": f"Bearer {tok}"},
        )
        assert r.status_code == 403


def test_feriados_filtra_por_anio(client, crear_usuario, token_staff):
    crear_usuario("pg-admin4@test.com", rol=RolUsuario.admin, nombre="Marcela")
    tok = token_staff("pg-admin4@test.com")
    r = client.get(
        "/api/v1/calendario-pagos/feriados", params={"anio": 2026}, headers={"Authorization": f"Bearer {tok}"}
    )
    assert r.status_code == 200, r.text
    feriados = r.json()
    assert len(feriados) > 0
    assert all(f["fecha"].startswith("2026-") for f in feriados)
