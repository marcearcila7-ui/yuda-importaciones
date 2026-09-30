from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.calendario_pagos import PagoTarea
from app.models.cliente import Cliente
from app.models.user import User

# Misma lista que app/services/calendario_service.py::FERIADOS_CHINA (se
# duplica a propósito: son dos apps independientes, no vale la pena crear un
# módulo compartido por una lista estática). Ver ese archivo para el detalle
# de qué fechas son oficiales y cuáles son estimadas.
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


def _cliente_o_404(db: Session, cliente_id: str) -> Cliente:
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if cliente is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    return cliente


def crear_pago(db: Session, datos, usuario: User) -> PagoTarea:
    cliente = _cliente_o_404(db, datos.cliente_id)
    pago = PagoTarea(
        fecha=datos.fecha,
        tienda=datos.tienda,
        cliente_id=cliente.id,
        cliente_sigla=cliente.sigla or cliente.nombre,
        monto=datos.monto,
        estatus=datos.estatus,
        creado_por_id=usuario.id,
        creado_por_nombre=usuario.nombre,
    )
    db.add(pago)
    db.commit()
    db.refresh(pago)
    return pago


def actualizar_pago(db: Session, pago: PagoTarea, datos, usuario: User) -> PagoTarea:
    cliente = _cliente_o_404(db, datos.cliente_id)
    pago.fecha = datos.fecha
    pago.tienda = datos.tienda
    pago.cliente_id = cliente.id
    pago.cliente_sigla = cliente.sigla or cliente.nombre
    pago.monto = datos.monto
    pago.estatus = datos.estatus
    pago.actualizado_por_id = usuario.id
    pago.actualizado_por_nombre = usuario.nombre
    pago.actualizado_en = datetime.now(timezone.utc)

    db.commit()
    db.refresh(pago)
    return pago


def eliminar_pago(db: Session, pago: PagoTarea) -> None:
    db.delete(pago)
    db.commit()
