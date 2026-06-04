from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.core.config import settings
from app.core.security import hash_password
from app.database import get_db
from app.models.configuracion import Configuracion
from app.models.item import Item
from app.models.pedido import PedidoGenerado
from app.models.sesion import Sesion
from app.models.user import RolUsuario, User
from app.schemas.admin import (
    ConfiguracionResponse,
    ConfiguracionUpdate,
    UsuarioAdminResponse,
    UsuarioCreate,
    UsuarioUpdate,
)

# Router de administración (montado en /api/v1/admin)
router = APIRouter(prefix="/admin", tags=["admin"])

# Router de historial (montado en /api/v1/historial)
historial_router = APIRouter(prefix="/historial", tags=["historial"])

CLAVE_TIPO_CAMBIO = "tipo_cambio_usd"


# ──────────────── USUARIOS ────────────────


@router.get("/usuarios", response_model=list[UsuarioAdminResponse])
def listar_usuarios(
    usuario: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> list[User]:
    """Lista todos los usuarios ordenados por fecha de creación ascendente"""
    return db.query(User).order_by(User.created_at.asc()).all()


@router.post(
    "/usuarios", response_model=UsuarioAdminResponse, status_code=status.HTTP_201_CREATED
)
def crear_usuario(
    datos: UsuarioCreate,
    usuario: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> User:
    """Crea un usuario nuevo (email único)"""
    existe = db.query(User).filter(User.email == datos.email).first()
    if existe:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese email",
        )
    nuevo = User(
        nombre=datos.nombre,
        email=datos.email,
        hashed_password=hash_password(datos.password),
        rol=RolUsuario(datos.rol),
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioAdminResponse)
def actualizar_usuario(
    usuario_id: str,
    datos: UsuarioUpdate,
    usuario: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> User:
    """Actualiza nombre, rol o estado de un usuario"""
    objetivo = db.query(User).filter(User.id == usuario_id).first()
    if objetivo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )

    cambios = datos.model_dump(exclude_unset=True)

    # No permitir que el admin se desactive a sí mismo
    if usuario_id == usuario.id and cambios.get("activo") is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu propio usuario",
        )

    if "nombre" in cambios:
        objetivo.nombre = cambios["nombre"]
    if "rol" in cambios:
        objetivo.rol = RolUsuario(cambios["rol"])
    if "activo" in cambios:
        objetivo.activo = cambios["activo"]

    db.commit()
    db.refresh(objetivo)
    return objetivo


@router.post("/usuarios/{usuario_id}/reset-password")
def reset_password(
    usuario_id: str,
    nueva_password: str = Body(..., embed=True, min_length=6),
    usuario: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    """Reinicia la contraseña de un usuario"""
    objetivo = db.query(User).filter(User.id == usuario_id).first()
    if objetivo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )
    objetivo.hashed_password = hash_password(nueva_password)
    db.commit()
    return {"detail": "Contraseña actualizada"}


# ──────────────── CONFIGURACIÓN ────────────────


@router.get("/configuracion", response_model=ConfiguracionResponse)
def obtener_configuracion(
    usuario: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> ConfiguracionResponse:
    """Devuelve el tipo de cambio actual (o el default de settings)"""
    registro = (
        db.query(Configuracion).filter(Configuracion.clave == CLAVE_TIPO_CAMBIO).first()
    )
    if registro is None:
        return ConfiguracionResponse(
            tipo_cambio_usd=settings.TIPO_CAMBIO_USD, updated_at=None
        )
    return ConfiguracionResponse(
        tipo_cambio_usd=float(registro.valor), updated_at=registro.updated_at
    )


@router.patch("/configuracion", response_model=ConfiguracionResponse)
def actualizar_configuracion(
    datos: ConfiguracionUpdate,
    usuario: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> ConfiguracionResponse:
    """Crea o actualiza el tipo de cambio (upsert)"""
    registro = (
        db.query(Configuracion).filter(Configuracion.clave == CLAVE_TIPO_CAMBIO).first()
    )
    if registro is None:
        registro = Configuracion(
            clave=CLAVE_TIPO_CAMBIO, valor=str(datos.tipo_cambio_usd)
        )
        db.add(registro)
    else:
        registro.valor = str(datos.tipo_cambio_usd)
        registro.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(registro)
    return ConfiguracionResponse(
        tipo_cambio_usd=float(registro.valor), updated_at=registro.updated_at
    )


# ──────────────── MÉTRICAS ────────────────


@router.get("/metricas")
def metricas(
    usuario: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    """Métricas del mes actual para el dashboard (solo admin)"""
    ahora = datetime.now()
    inicio_mes = datetime(ahora.year, ahora.month, 1)
    if ahora.month == 12:
        fin_mes = datetime(ahora.year + 1, 1, 1)
    else:
        fin_mes = datetime(ahora.year, ahora.month + 1, 1)

    # Sesiones creadas este mes
    sesiones_mes = (
        db.query(Sesion)
        .filter(Sesion.created_at >= inicio_mes, Sesion.created_at < fin_mes)
        .all()
    )
    ids_sesiones = [s.id for s in sesiones_mes]

    # Ítems de esas sesiones
    items = (
        db.query(Item).filter(Item.sesion_id.in_(ids_sesiones)).all()
        if ids_sesiones
        else []
    )
    total_rmb_mes = sum(
        (i.price_rmb or 0) * (i.qty_por_ctn or 0) * (i.ctns or 0) for i in items
    )

    # Tipo de cambio: tabla configuracion o valor por defecto de settings
    registro_tc = (
        db.query(Configuracion).filter(Configuracion.clave == CLAVE_TIPO_CAMBIO).first()
    )
    tipo_cambio = float(registro_tc.valor) if registro_tc else settings.TIPO_CAMBIO_USD

    total_usd_mes = round(total_rmb_mes / tipo_cambio, 2) if tipo_cambio else 0.0
    proveedores = {(i.supplier_nombre, i.supplier_numero) for i in items}

    # Pedidos generados este mes
    total_pedidos_mes = (
        db.query(PedidoGenerado)
        .filter(
            PedidoGenerado.fecha_generacion >= inicio_mes,
            PedidoGenerado.fecha_generacion < fin_mes,
        )
        .count()
    )

    return {
        "total_sesiones_mes": len(sesiones_mes),
        "total_rmb_mes": total_rmb_mes,
        "total_usd_mes": total_usd_mes,
        "total_items_mes": len(items),
        "total_pedidos_mes": total_pedidos_mes,
        "proveedores_unicos_mes": len(proveedores),
    }


@router.get("/metricas-vendedoras")
def metricas_vendedoras(
    usuario: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    """Métricas del mes actual desglosadas por cada vendedora (solo admin)"""
    ahora = datetime.now()
    inicio_mes = datetime(ahora.year, ahora.month, 1)
    if ahora.month == 12:
        fin_mes = datetime(ahora.year + 1, 1, 1)
    else:
        fin_mes = datetime(ahora.year, ahora.month + 1, 1)

    vendedoras = (
        db.query(User).filter(User.rol == RolUsuario.vendedora).order_by(User.nombre.asc()).all()
    )

    resultado = []
    for v in vendedoras:
        sesiones = (
            db.query(Sesion)
            .filter(
                Sesion.user_id == v.id,
                Sesion.created_at >= inicio_mes,
                Sesion.created_at < fin_mes,
            )
            .all()
        )
        total_items = 0
        total_rmb = 0.0
        total_usd = 0.0
        for s in sesiones:
            items = db.query(Item).filter(Item.sesion_id == s.id).all()
            total_items += len(items)
            sesion_rmb = sum(
                (i.price_rmb or 0) * (i.qty_por_ctn or 0) * (i.ctns or 0) for i in items
            )
            total_rmb += sesion_rmb
            if s.tipo_cambio_usd:
                total_usd += sesion_rmb / s.tipo_cambio_usd
        resultado.append(
            {
                "user_id": v.id,
                "nombre": v.nombre,
                "total_sesiones": len(sesiones),
                "total_items": total_items,
                "total_rmb": round(total_rmb, 2),
                "total_usd": round(total_usd, 2),
            }
        )

    return {"vendedoras": resultado}


# ──────────────── HISTORIAL ────────────────


@historial_router.get("/sesiones")
def historial_sesiones(
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    nombre_cliente: Optional[str] = Query(None),
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Historial de cotizaciones con totales financieros (admin y contadora)"""
    query = db.query(Sesion)
    if fecha_desde:
        query = query.filter(Sesion.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Sesion.fecha <= fecha_hasta)
    if nombre_cliente:
        query = query.filter(Sesion.nombre_cliente.ilike(f"%{nombre_cliente}%"))

    sesiones = query.order_by(Sesion.fecha.desc()).all()

    resultado = []
    for sesion in sesiones:
        items = db.query(Item).filter(Item.sesion_id == sesion.id).all()
        total_items = len(items)
        total_rmb = sum((i.price_rmb or 0) * (i.qty_por_ctn or 0) * (i.ctns or 0) for i in items)
        total_usd = round(total_rmb / sesion.tipo_cambio_usd, 4) if sesion.tipo_cambio_usd else 0.0
        proveedores = {(i.supplier_nombre, i.supplier_numero) for i in items}
        tiene_pedidos = (
            db.query(PedidoGenerado.id)
            .filter(PedidoGenerado.sesion_id == sesion.id)
            .first()
            is not None
        )
        resultado.append(
            {
                "id": sesion.id,
                "nombre_cliente": sesion.nombre_cliente,
                "fecha": sesion.fecha,
                "total_items": total_items,
                "total_rmb": total_rmb,
                "total_usd": total_usd,
                "cantidad_proveedores": len(proveedores),
                "tiene_pedidos": tiene_pedidos,
                "created_at": sesion.created_at,
            }
        )
    return resultado
