from datetime import date, datetime, time, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.core.config import settings
from app.core.security import hash_password
from app.database import get_db
from app.models.cliente import Cliente
from app.models.configuracion import Configuracion
from app.models.item import Item
from app.models.pedido import PedidoGenerado
from app.models.seguimiento import ESTADOS_ENVIO, SeguimientoPedido
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
    """Crea un usuario nuevo (email único).

    El email se guarda normalizado (sin espacios, en minúsculas): el login
    comparaba distinguiendo mayúsculas/minúsculas, así que un usuario creado
    como "Nombre@Correo.com" no podía entrar escribiendo "nombre@correo.com"
    y viceversa — el mensaje "credenciales incorrectas" no dejaba ver que la
    cuenta sí existía, solo que la búsqueda no la encontraba.
    """
    email = datos.email.strip().lower()
    # func.lower(): atrapa también un usuario viejo guardado con mayúsculas
    # de antes de este arreglo (si no, se podría crear un duplicado).
    existe = db.query(User).filter(func.lower(User.email) == email).first()
    if existe:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese email",
        )
    nuevo = User(
        nombre=datos.nombre,
        email=email,
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
    # Invalida las sesiones abiertas del usuario con la contraseña vieja.
    objetivo.token_version = (objetivo.token_version or 0) + 1
    db.commit()
    return {"detail": "Contraseña actualizada"}


# ──────────────── CONFIGURACIÓN ────────────────


@router.get("/configuracion", response_model=ConfiguracionResponse)
def obtener_configuracion(
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> ConfiguracionResponse:
    """Devuelve el tipo de cambio actual (o el default de settings). Lo leen tanto
    la admin como las vendedoras (para precargarlo al crear una cotización)."""
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


# Etapas en las que el contenedor ya está despachado (en tránsito en adelante).
ESTADOS_DESPACHADO = tuple(ESTADOS_ENVIO[ESTADOS_ENVIO.index("en_transito"):])
BOGOTA = ZoneInfo("America/Bogota")


def _rango_utc(desde: date | None, hasta: date | None) -> tuple[datetime | None, datetime | None]:
    """Convierte un rango de fechas en hora Bogotá a límites en UTC (para comparar
    contra los timestamps guardados). `hasta` incluye todo el día."""
    ini = (
        datetime.combine(desde, time.min).replace(tzinfo=BOGOTA).astimezone(timezone.utc)
        if desde
        else None
    )
    fin = (
        datetime.combine(hasta, time.max).replace(tzinfo=BOGOTA).astimezone(timezone.utc)
        if hasta
        else None
    )
    return ini, fin


def _numero_cotizacion(sesion: Sesion) -> str:
    return f"YUDA-{sesion.fecha:%Y%m%d}-{sesion.id[:6].upper()}"


@router.get("/ventas")
def panel_ventas(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    vendedora_id: str | None = Query(None),
    usuario: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    """Panel de ventas de Marcela (solo admin).

    Devuelve montos vendidos, pedidos en tránsito, cotizaciones enviadas y
    contenedores despachados, con el desglose por vendedora y el detalle de cada
    despacho. Filtra por rango de fechas (hora Bogotá) y por vendedora. Alimenta
    el resumen del dashboard, la pestaña Ventas y la exportación a CSV.
    """
    ini, fin = _rango_utc(desde, hasta)

    # ---- Despachos: contenedores en tránsito en adelante ----
    q = (
        db.query(SeguimientoPedido, Sesion, User)
        .join(Sesion, SeguimientoPedido.sesion_id == Sesion.id)
        .join(User, Sesion.user_id == User.id)
        .filter(SeguimientoPedido.estado.in_(ESTADOS_DESPACHADO))
    )
    if ini is not None:
        q = q.filter(SeguimientoPedido.despachado_at >= ini)
    if fin is not None:
        q = q.filter(SeguimientoPedido.despachado_at <= fin)
    if vendedora_id:
        q = q.filter(Sesion.user_id == vendedora_id)
    filas = q.order_by(SeguimientoPedido.despachado_at.desc().nullslast()).all()

    despachos: list[dict] = []
    ventas_total = 0.0
    ventas_vendedoras = 0.0
    contenedores_vendedoras = 0
    en_transito = 0
    agg_vend: dict[str, dict] = {}
    sin_monto = 0
    for seg, ses, creador in filas:
        # Un despacho sin monto cargado suma 0. No es un error de calculo, es un
        # dato que falta, y hay que decirlo: si no, el panel muestra contenedores
        # despachados con $0,00 en ventas y parece que la cuenta esta rota.
        if seg.monto_venta is None:
            sin_monto += 1
        monto = float(seg.monto_venta) if seg.monto_venta is not None else 0.0
        ventas_total += monto
        es_vend = creador.rol == RolUsuario.vendedora
        if es_vend:
            ventas_vendedoras += monto
            contenedores_vendedoras += 1
            a = agg_vend.setdefault(creador.id, {"contenedores": 0, "ventas": 0.0})
            a["contenedores"] += 1
            a["ventas"] += monto
        if seg.estado == "en_transito":
            en_transito += 1
        despachos.append(
            {
                "sesion_id": ses.id,
                "numero": _numero_cotizacion(ses),
                "cliente": ses.nombre_cliente,
                "vendedora": creador.nombre,
                "es_vendedora": es_vend,
                "estado": seg.estado,
                "bl_numero": seg.bl_numero,
                "naviera": seg.naviera,
                "monto_venta": round(monto, 2),
                "despachado_at": seg.despachado_at.isoformat() if seg.despachado_at else None,
                "fecha_cotizacion": ses.fecha.isoformat(),
            }
        )

    # Despachos que existen pero caen fuera del periodo elegido. Sin este dato,
    # un panel en cero no distingue entre "no hubo ventas" y "estas mirando el
    # periodo equivocado", y las dos cosas se ven igual.
    fuera_periodo = 0
    if ini is not None or fin is not None:
        q_todos = (
            db.query(SeguimientoPedido)
            .join(Sesion, SeguimientoPedido.sesion_id == Sesion.id)
            .filter(SeguimientoPedido.estado.in_(ESTADOS_DESPACHADO))
        )
        if vendedora_id:
            q_todos = q_todos.filter(Sesion.user_id == vendedora_id)
        fuera_periodo = max(0, q_todos.count() - len(filas))

    # ---- Cotizaciones enviadas (archivos enviados al cliente) ----
    qc = db.query(Sesion.user_id).filter(Sesion.enviada_cliente.is_(True))
    if ini is not None:
        qc = qc.filter(Sesion.created_at >= ini)
    if fin is not None:
        qc = qc.filter(Sesion.created_at <= fin)
    if vendedora_id:
        qc = qc.filter(Sesion.user_id == vendedora_id)
    cot_por_user: dict[str, int] = {}
    for (uid,) in qc.all():
        cot_por_user[uid] = cot_por_user.get(uid, 0) + 1
    cotizaciones_hechas = sum(cot_por_user.values())

    # ---- Desglose por vendedora ----
    vendedoras = (
        db.query(User).filter(User.rol == RolUsuario.vendedora).order_by(User.nombre.asc()).all()
    )
    por_vendedora = []
    for v in vendedoras:
        if vendedora_id and v.id != vendedora_id:
            continue
        a = agg_vend.get(v.id, {"contenedores": 0, "ventas": 0.0})
        por_vendedora.append(
            {
                "vendedora_id": v.id,
                "nombre": v.nombre,
                "cotizaciones": cot_por_user.get(v.id, 0),
                "contenedores": a["contenedores"],
                "ventas": round(a["ventas"], 2),
            }
        )

    return {
        "desde": desde.isoformat() if desde else None,
        "hasta": hasta.isoformat() if hasta else None,
        "ventas_total": round(ventas_total, 2),
        "pedidos_en_transito": en_transito,
        "cotizaciones_hechas": cotizaciones_hechas,
        "contenedores_total": len(despachos),
        "contenedores_vendedoras": contenedores_vendedoras,
        "contenedores_sin_monto": sin_monto,
        "despachos_fuera_periodo": fuera_periodo,
        "ventas_vendedoras": round(ventas_vendedoras, 2),
        "por_vendedora": por_vendedora,
        "despachos": despachos,
    }


@router.get("/equipo")
def panorama_equipo(
    usuario: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    """Panorama para Marcela: cada vendedora con sus clientes y el envío de cada cotización"""
    vendedoras = (
        db.query(User).filter(User.rol == RolUsuario.vendedora).order_by(User.nombre.asc()).all()
    )

    resultado = []
    for v in vendedoras:
        clientes = (
            db.query(Cliente)
            .filter(Cliente.vendedora_id == v.id)
            .order_by(Cliente.nombre.asc())
            .all()
        )
        lista_clientes = []
        for c in clientes:
            sesiones = (
                db.query(Sesion)
                .filter(Sesion.cliente_id == c.id)
                .order_by(Sesion.created_at.desc())
                .all()
            )
            cotizaciones = []
            for s in sesiones:
                seg = (
                    db.query(SeguimientoPedido)
                    .filter(SeguimientoPedido.sesion_id == s.id)
                    .first()
                )
                # Pendiente de BL: lista para envío o en tránsito y sin BL cargado.
                # Es lo que Marcela debe atender.
                pendiente_bl = bool(
                    seg
                    and seg.estado in ("en_bodega", "en_transito")
                    and not seg.bl_numero
                )
                cotizaciones.append(
                    {
                        "sesion_id": s.id,
                        "numero": f"YUDA-{s.fecha:%Y%m%d}-{s.id[:6].upper()}",
                        "fecha": s.fecha.isoformat(),
                        "nombre_cliente": s.nombre_cliente,
                        "enviada": s.enviada_cliente,
                        "estado": seg.estado if seg else None,
                        "naviera": seg.naviera if seg else None,
                        "numero_tracking": seg.numero_tracking if seg else None,
                        "bl_numero": seg.bl_numero if seg else None,
                        "bl_pdf_url": seg.bl_pdf_url if seg else None,
                        "pendiente_bl": pendiente_bl,
                    }
                )
            lista_clientes.append(
                {
                    "id": c.id,
                    "nombre": c.nombre,
                    "email": c.email,
                    "empresa": c.empresa,
                    "pais": c.pais,
                    "activo": c.activo,
                    "cotizaciones": cotizaciones,
                }
            )
        resultado.append(
            {
                "user_id": v.id,
                "nombre": v.nombre,
                "email": v.email,
                "total_clientes": len(lista_clientes),
                "clientes": lista_clientes,
            }
        )

    return {"vendedoras": resultado}


# ──────────────── HISTORIAL ────────────────


@historial_router.get("/sesiones")
def historial_sesiones(
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    nombre_cliente: Optional[str] = Query(None),
    # Paginación opcional: sin `limit` devuelve todo (comportamiento anterior);
    # el frontend pide de a páginas con "Cargar más" para no traer cientos de golpe.
    limit: Optional[int] = Query(None, ge=1, le=200),
    offset: int = Query(0, ge=0),
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

    query = query.order_by(Sesion.fecha.desc())
    if limit is not None:
        query = query.limit(limit).offset(offset)
    sesiones = query.all()

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
