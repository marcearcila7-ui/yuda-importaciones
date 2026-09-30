"""Calendario compartido: crear/editar una tarea debe avisarle a TODO el
staff activo (admin + vendedora + bodega, nunca contadora ni clientes), con
su propia notificación separada de las demás apps; una edición debe dejar
registrado quién la editó por última vez, y roles sin acceso no deben poder
entrar."""
from app.models.calendario import CalendarioNotificacion
from app.models.user import RolUsuario


def test_crear_tarea_avisa_a_todo_el_staff_activo(db, client, crear_usuario, token_staff):
    admin = crear_usuario("cal-admin1@test.com", rol=RolUsuario.admin, nombre="Marcela")
    vendedora = crear_usuario("cal-v1@test.com", rol=RolUsuario.vendedora, nombre="Vendedora Uno")
    bodega = crear_usuario("cal-b1@test.com", rol=RolUsuario.bodega, nombre="Bodega Uno")
    # contadora activa e inactiva: ninguna debe enterarse.
    crear_usuario("cal-c1@test.com", rol=RolUsuario.contadora, nombre="Contadora")
    crear_usuario("cal-v2-inactiva@test.com", rol=RolUsuario.vendedora, nombre="Inactiva", activo=False)

    tok = token_staff("cal-v1@test.com")
    r = client.post(
        "/api/v1/calendario/tareas",
        json={"fecha": "2026-10-05", "tipo": "recibe", "marca_cliente": "ABC", "descripcion": "Contenedor 1"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["tipo"] == "recibe"
    assert data["creado_por_nombre"] == "Vendedora Uno"
    assert data["actualizado_por_id"] is None

    avisos = db.query(CalendarioNotificacion).filter(CalendarioNotificacion.tarea_id == data["id"]).all()
    destinatarios = {a.usuario_id for a in avisos}
    assert destinatarios == {admin.id, vendedora.id, bodega.id}


def test_editar_tarea_registra_quien_edito_y_avisa_de_nuevo(db, client, crear_usuario, token_staff):
    crear_usuario("cal-admin2@test.com", rol=RolUsuario.admin, nombre="Marcela")
    vendedora = crear_usuario("cal-v3@test.com", rol=RolUsuario.vendedora, nombre="Vendedora Tres")
    bodega = crear_usuario("cal-b2@test.com", rol=RolUsuario.bodega, nombre="Bodega Dos")

    tok_v = token_staff("cal-v3@test.com")
    r = client.post(
        "/api/v1/calendario/tareas",
        json={"fecha": "2026-10-05", "tipo": "carga", "marca_cliente": "XYZ", "descripcion": "Original"},
        headers={"Authorization": f"Bearer {tok_v}"},
    )
    tarea_id = r.json()["id"]

    tok_b = token_staff("cal-b2@test.com")
    r2 = client.put(
        f"/api/v1/calendario/tareas/{tarea_id}",
        json={"fecha": "2026-10-06", "tipo": "carga", "marca_cliente": "XYZ", "descripcion": "Corregida"},
        headers={"Authorization": f"Bearer {tok_b}"},
    )
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert data["descripcion"] == "Corregida"
    assert data["actualizado_por_nombre"] == "Bodega Dos"
    assert data["actualizado_en"] is not None
    # La creación no se pisa.
    assert data["creado_por_nombre"] == "Vendedora Tres"

    avisos = db.query(CalendarioNotificacion).filter(CalendarioNotificacion.tarea_id == tarea_id).all()
    assert len(avisos) == 6  # 3 al crear + 3 al editar (admin+vendedora+bodega cada vez)


def test_contadora_no_tiene_acceso_al_calendario(client, crear_usuario, token_staff):
    crear_usuario("cal-c2@test.com", rol=RolUsuario.contadora, nombre="Contadora Dos")
    tok = token_staff("cal-c2@test.com")
    r = client.get(
        "/api/v1/calendario/tareas",
        params={"desde": "2026-10-01", "hasta": "2026-10-31"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 403


def test_feriados_filtra_por_anio(client, crear_usuario, token_staff):
    crear_usuario("cal-admin3@test.com", rol=RolUsuario.admin, nombre="Marcela")
    tok = token_staff("cal-admin3@test.com")
    r = client.get("/api/v1/calendario/feriados", params={"anio": 2026}, headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200, r.text
    feriados = r.json()
    assert len(feriados) > 0
    assert all(f["fecha"].startswith("2026-") for f in feriados)
