from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.calendario import (
    TIPO_TAREA_ACTUALIZADA,
    TIPO_TAREA_CREADA,
    CalendarioNotificacion,
    CalendarioTarea,
)
from app.models.user import RolUsuario, User

# Feriados oficiales y fechas comerciales importantes de China. Los de fecha
# fija (1 ene, 1 may, 1 oct) son exactos. Los de calendario lunar (Año Nuevo
# Chino, Qingming, Dragon Boat, Medio Otoño) del 2026 corresponden al
# calendario oficial ya publicado; los del 2027 son un estimado (el
# calendario oficial chino recién se publica en noviembre/diciembre del año
# anterior) -conviene confirmarlos cuando China los publique y avisarle a
# Claude para actualizar esta lista.
FERIADOS_CHINA: list[dict] = [
    {"fecha": date(2026, 1, 1), "nombre_es": "Año Nuevo", "nombre_en": "New Year's Day"},
    {"fecha": date(2026, 2, 17), "nombre_es": "Año Nuevo Chino (Fiesta de Primavera)", "nombre_en": "Chinese New Year (Spring Festival)"},
    {"fecha": date(2026, 4, 5), "nombre_es": "Festival Qingming (Tomb-Sweeping)", "nombre_en": "Qingming Festival"},
    {"fecha": date(2026, 5, 1), "nombre_es": "Día Internacional del Trabajo", "nombre_en": "Labour Day"},
    {"fecha": date(2026, 6, 19), "nombre_es": "Festival del Bote del Dragón", "nombre_en": "Dragon Boat Festival"},
    {"fecha": date(2026, 9, 25), "nombre_es": "Festival del Medio Otoño", "nombre_en": "Mid-Autumn Festival"},
    {"fecha": date(2026, 10, 1), "nombre_es": "Día Nacional (Semana Dorada)", "nombre_en": "National Day (Golden Week)"},
    {"fecha": date(2026, 11, 11), "nombre_es": "Día del Soltero (11.11)", "nombre_en": "Singles' Day (11.11)"},
    {"fecha": date(2027, 1, 1), "nombre_es": "Año Nuevo", "nombre_en": "New Year's Day"},
    {"fecha": date(2027, 2, 6), "nombre_es": "Año Nuevo Chino (estimado, verificar)", "nombre_en": "Chinese New Year (estimated, verify)"},
    {"fecha": date(2027, 4, 5), "nombre_es": "Festival Qingming (Tomb-Sweeping)", "nombre_en": "Qingming Festival"},
    {"fecha": date(2027, 5, 1), "nombre_es": "Día Internacional del Trabajo", "nombre_en": "Labour Day"},
    {"fecha": date(2027, 6, 9), "nombre_es": "Festival del Bote del Dragón (estimado, verificar)", "nombre_en": "Dragon Boat Festival (estimated, verify)"},
    {"fecha": date(2027, 9, 15), "nombre_es": "Festival del Medio Otoño (estimado, verificar)", "nombre_en": "Mid-Autumn Festival (estimated, verify)"},
    {"fecha": date(2027, 10, 1), "nombre_es": "Día Nacional (Semana Dorada)", "nombre_en": "National Day (Golden Week)"},
    {"fecha": date(2027, 11, 11), "nombre_es": "Día del Soltero (11.11)", "nombre_en": "Singles' Day (11.11)"},
]


def feriados_del_anio(anio: int) -> list[dict]:
    return [f for f in FERIADOS_CHINA if f["fecha"].year == anio]


def _staff_activo(db: Session) -> list[User]:
    """Admin + vendedora + bodega activos: los únicos con acceso al
    calendario, así que son los únicos que deben enterarse de una tarea
    nueva o editada."""
    return (
        db.query(User)
        .filter(
            User.rol.in_([RolUsuario.admin, RolUsuario.vendedora, RolUsuario.bodega]),
            User.activo.is_(True),
        )
        .all()
    )


def _crear_notificaciones_staff(
    db: Session, tarea: CalendarioTarea, tipo_aviso: str, titulo: str, mensaje: str
) -> list[str]:
    """Le avisa a TODO el staff (incluido quien creó/editó la tarea): así lo
    pidió Marcela. Cada uno recibe su propio aviso en la campanita de esta
    app -nunca en las notificaciones del cotizador ni de Yuda Logistic.

    Solo crea las filas en la base (rápido, parte de la misma transacción
    que guarda la tarea). El envío del push en sí se hace aparte, en
    segundo plano (ver rutas), para que avisarle a todo el staff nunca
    alargue la respuesta cuando varias personas usan el calendario a la vez.
    """
    staff = _staff_activo(db)
    for usuario in staff:
        db.add(
            CalendarioNotificacion(
                usuario_id=usuario.id,
                tarea_id=tarea.id,
                tipo=tipo_aviso,
                titulo=titulo,
                mensaje=mensaje,
            )
        )
    return [u.id for u in staff]


def crear_tarea(db: Session, datos, usuario: User) -> tuple[CalendarioTarea, list[str], str, str]:
    tarea = CalendarioTarea(
        fecha=datos.fecha,
        tipo=datos.tipo,
        marca_cliente=datos.marca_cliente,
        descripcion=datos.descripcion,
        creado_por_id=usuario.id,
        creado_por_nombre=usuario.nombre,
    )
    db.add(tarea)
    db.flush()  # necesita tarea.id antes de armar las notificaciones

    titulo = f"Nueva tarea: {datos.tipo} · {datos.marca_cliente}"
    mensaje = f"{usuario.nombre} agregó una tarea para el {datos.fecha:%d/%m/%Y}"
    staff_ids = _crear_notificaciones_staff(db, tarea, TIPO_TAREA_CREADA, titulo, mensaje)

    db.commit()
    db.refresh(tarea)
    return tarea, staff_ids, titulo, mensaje


def actualizar_tarea(
    db: Session, tarea: CalendarioTarea, datos, usuario: User
) -> tuple[CalendarioTarea, list[str], str, str]:
    tarea.fecha = datos.fecha
    tarea.tipo = datos.tipo
    tarea.marca_cliente = datos.marca_cliente
    tarea.descripcion = datos.descripcion
    tarea.actualizado_por_id = usuario.id
    tarea.actualizado_por_nombre = usuario.nombre
    tarea.actualizado_en = datetime.now(timezone.utc)

    titulo = f"Tarea editada: {datos.tipo} · {datos.marca_cliente}"
    mensaje = f"{usuario.nombre} editó la tarea del {datos.fecha:%d/%m/%Y}"
    staff_ids = _crear_notificaciones_staff(db, tarea, TIPO_TAREA_ACTUALIZADA, titulo, mensaje)

    db.commit()
    db.refresh(tarea)
    return tarea, staff_ids, titulo, mensaje
