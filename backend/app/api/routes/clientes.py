import asyncio
import secrets
import string
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.database import get_db
from app.models.cliente import Cliente
from app.models.cuenta import MovimientoCuenta, calcular_comision
from app.models.seguimiento import (
    CAMPOS_SOLO_ADMIN,
    ESTADO_DISPARA_AVISO,
    ESTADO_INICIAL,
    ESTADOS_ENVIO,
    ESTADOS_VENDEDORA,
    SeguimientoPedido,
)
from app.models.item import Item
from app.models.sesion import PEDIDO_POR_CONFIRMAR, Sesion
from app.models.user import User
from app.schemas.cliente import (
    ClienteCreado,
    ClienteCreate,
    ClienteResponse,
    ClienteUpdate,
    ResetPasswordRequest,
)
from app.schemas.cuenta import (
    EstadoCuentaResponse,
    MovimientoCreate,
    MovimientoUpdate,
)
from app.schemas.packing import EnviarAConfirmarInput, SesionResponse
from app.schemas.seguimiento import SeguimientoResponse, SeguimientoUpdate
from app.services.cuenta_service import construir_estado_cuenta
from app.services.notificacion_service import (
    avisar_envio_a_vendedora,
    avisar_listo_para_envio,
)
from app.services.storage_service import subir_foto, subir_pdf
from app.core.security import hash_password

# Se monta en main.py bajo /api/v1 (sin prefijo propio)
router = APIRouter(tags=["clientes"])


def _generar_password(n: int = 10) -> str:
    """Contraseña inicial aleatoria fácil de copiar (sin ambigüedades visuales)"""
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
    return "".join(secrets.choice(alfabeto) for _ in range(n))


def _cliente_autorizado(db: Session, cliente_id: str, usuario: User) -> Cliente:
    """Devuelve el cliente si el usuario puede gestionarlo; si no, 404/403"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if cliente is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    if usuario.rol.value == "vendedora" and cliente.vendedora_id != usuario.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin permisos sobre este cliente")
    return cliente


def _sesion_autorizada(db: Session, sesion_id: str, usuario: User) -> Sesion:
    """Devuelve la sesión si el usuario puede gestionarla; si no, 404/403"""
    sesion = db.query(Sesion).filter(Sesion.id == sesion_id).first()
    if sesion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cotización no encontrada")
    if usuario.rol.value == "vendedora" and sesion.user_id != usuario.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin permisos sobre esta cotización")
    return sesion


# ──────────────── CLIENTES (CRUD) ────────────────


@router.post("/clientes", response_model=ClienteCreado, status_code=status.HTTP_201_CREATED)
def crear_cliente(
    datos: ClienteCreate,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> ClienteCreado:
    """Crea un cliente con acceso al portal. La vendedora queda como dueña."""
    email = datos.email.strip().lower()
    if db.query(Cliente).filter(Cliente.email == email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un cliente con ese email")

    password = (datos.password or "").strip() or _generar_password()
    cliente = Cliente(
        nombre=datos.nombre.strip(),
        email=email,
        empresa=datos.empresa,
        nit=datos.nit,
        telefono=datos.telefono,
        pais=datos.pais,
        hashed_password=hash_password(password),
        vendedora_id=usuario.id,
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)

    return ClienteCreado(
        **ClienteResponse.model_validate(cliente).model_dump(),
        password_inicial=password,
    )


@router.get("/clientes", response_model=list[ClienteResponse])
def listar_clientes(
    usuario: User = Depends(require_roles("admin", "vendedora", "contadora")),
    db: Session = Depends(get_db),
) -> list[Cliente]:
    """Lista clientes: la vendedora ve los suyos, admin y contadora ven todos."""
    query = db.query(Cliente)
    if usuario.rol.value == "vendedora":
        query = query.filter(Cliente.vendedora_id == usuario.id)
    return query.order_by(Cliente.created_at.desc()).all()


@router.get("/clientes/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente(
    cliente_id: str,
    # La contadora ve la ficha del cliente en solo lectura (para conciliar).
    usuario: User = Depends(require_roles("admin", "vendedora", "contadora")),
    db: Session = Depends(get_db),
) -> Cliente:
    return _cliente_autorizado(db, cliente_id, usuario)


@router.get("/clientes/{cliente_id}/cotizaciones", response_model=list[SesionResponse])
def cotizaciones_del_cliente(
    cliente_id: str,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> list[Sesion]:
    """Cotizaciones vinculadas a un cliente"""
    _cliente_autorizado(db, cliente_id, usuario)
    return (
        db.query(Sesion)
        .filter(Sesion.cliente_id == cliente_id)
        .order_by(Sesion.created_at.desc())
        .all()
    )


@router.patch("/clientes/{cliente_id}", response_model=ClienteResponse)
def actualizar_cliente(
    cliente_id: str,
    datos: ClienteUpdate,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> Cliente:
    cliente = _cliente_autorizado(db, cliente_id, usuario)
    cambios = datos.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(cliente, campo, valor)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.delete("/clientes/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cliente(
    cliente_id: str,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> None:
    """Elimina un cliente. Se bloquea si tiene cotizaciones ya enviadas (tienen
    seguimiento/portal activos); en ese caso conviene desactivarlo. Las cotizaciones
    sin enviar se desvinculan para no perder el trabajo.
    """
    cliente = _cliente_autorizado(db, cliente_id, usuario)

    enviadas = (
        db.query(Sesion)
        .filter(Sesion.cliente_id == cliente_id, Sesion.enviada_cliente.is_(True))
        .count()
    )
    if enviadas:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este cliente tiene cotizaciones enviadas con seguimiento activo. "
            "Desactívalo en lugar de eliminarlo.",
        )

    # Desvincula las cotizaciones sin enviar para conservarlas
    db.query(Sesion).filter(Sesion.cliente_id == cliente_id).update(
        {Sesion.cliente_id: None}
    )
    db.delete(cliente)
    db.commit()


@router.post("/clientes/{cliente_id}/reset-password")
def reset_password_cliente(
    cliente_id: str,
    datos: ResetPasswordRequest,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> dict:
    cliente = _cliente_autorizado(db, cliente_id, usuario)
    nueva = datos.nueva_password.strip()
    if len(nueva) < 6:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contraseña debe tener al menos 6 caracteres")
    cliente.hashed_password = hash_password(nueva)
    # Invalida las sesiones abiertas del cliente con la contraseña vieja.
    cliente.token_version = (cliente.token_version or 0) + 1
    db.commit()
    return {"detail": "Contraseña actualizada"}


# ──────────────── VÍNCULO COTIZACIÓN ↔ CLIENTE ────────────────


class VincularClienteRequest(BaseModel):
    cliente_id: str | None = None


@router.patch("/sesiones/{sesion_id}/cliente", response_model=SesionResponse)
def vincular_cliente(
    sesion_id: str,
    datos: VincularClienteRequest,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> Sesion:
    """Vincula (o desvincula) una cotización con un cliente del portal"""
    sesion = _sesion_autorizada(db, sesion_id, usuario)

    if datos.cliente_id is None:
        sesion.cliente_id = None
        sesion.enviada_cliente = False
        sesion.fecha_envio_cliente = None
    else:
        _cliente_autorizado(db, datos.cliente_id, usuario)
        sesion.cliente_id = datos.cliente_id

    db.commit()
    db.refresh(sesion)
    return sesion


@router.post("/sesiones/{sesion_id}/enviar-cliente", response_model=SeguimientoResponse)
def enviar_a_cliente(
    sesion_id: str,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> SeguimientoPedido:
    """Marca la cotización como enviada al cliente y crea su seguimiento"""
    sesion = _sesion_autorizada(db, sesion_id, usuario)
    if not sesion.cliente_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Primero asigna un cliente a esta cotización",
        )

    sesion.enviada_cliente = True
    sesion.fecha_envio_cliente = datetime.now()

    seg = db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == sesion_id).first()
    if seg is None:
        ahora = datetime.now(timezone.utc)
        seg = SeguimientoPedido(
            sesion_id=sesion_id,
            estado=ESTADO_INICIAL,
            hitos={
                ESTADO_INICIAL: {
                    "fecha": ahora.date().isoformat(),
                    "nota": None,
                    "ts": ahora.isoformat(),
                }
            },
        )
        db.add(seg)

    db.commit()
    db.refresh(seg)
    return seg


@router.put("/sesiones/{sesion_id}/enviar-a-confirmar", response_model=SesionResponse)
def enviar_a_confirmar(
    sesion_id: str,
    datos: EnviarAConfirmarInput,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> Sesion:
    """La vendedora ajusta las cantidades y le devuelve al cliente la cotización
    para su confirmación final (estado "por confirmar"). El cliente confirma desde
    el portal; recién ahí se puede generar el pedido al proveedor."""
    sesion = _sesion_autorizada(db, sesion_id, usuario)
    items = {i.id: i for i in db.query(Item).filter(Item.sesion_id == sesion_id).all()}
    for linea in datos.items:
        it = items.get(linea.item_id)
        if it is None:
            continue
        it.cantidad_solicitada = linea.cantidad if linea.cantidad and linea.cantidad > 0 else None
    sesion.pedido_estado = PEDIDO_POR_CONFIRMAR
    sesion.pedido_confirmado_at = None
    if sesion.pedido_recibido_at is None:
        sesion.pedido_recibido_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(sesion)
    return sesion


@router.get("/sesiones/{sesion_id}/seguimiento", response_model=SeguimientoResponse)
def obtener_seguimiento(
    sesion_id: str,
    usuario: User = Depends(require_roles("admin", "vendedora", "contadora")),
    db: Session = Depends(get_db),
) -> SeguimientoPedido:
    """Seguimiento de una cotización (staff)"""
    _sesion_autorizada(db, sesion_id, usuario)
    seg = db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == sesion_id).first()
    if seg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esta cotización aún no se envió al cliente")
    return seg


@router.put("/sesiones/{sesion_id}/seguimiento", response_model=SeguimientoResponse)
def actualizar_seguimiento(
    sesion_id: str,
    datos: SeguimientoUpdate,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> SeguimientoPedido:
    """Crea o actualiza el seguimiento del envío de una cotización.

    La vendedora gestiona las etapas hasta "en bodega" y las notas/fechas de
    cada hito. Cuando el contenedor está en camino (naviera, tracking, BL, ETA
    y las etapas de tránsito en adelante) la información es exclusiva de Marcela.
    """
    sesion = _sesion_autorizada(db, sesion_id, usuario)
    es_vendedora = usuario.rol.value == "vendedora"

    seg = db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == sesion_id).first()
    if seg is None:
        seg = SeguimientoPedido(sesion_id=sesion_id, estado=ESTADO_INICIAL)
        db.add(seg)

    estado_anterior = seg.estado

    # La vendedora no puede mover ni tocar el envío una vez está en tránsito.
    if es_vendedora:
        if estado_anterior not in ESTADOS_VENDEDORA:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Esta cotización ya está en tránsito; la gestiona Marcela",
            )
        if datos.estado not in ESTADOS_VENDEDORA:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "La etapa de envío (en tránsito en adelante) la gestiona Marcela",
            )

    # Campos que cualquiera del equipo autorizado puede actualizar
    seg.estado = datos.estado
    seg.novedades = datos.novedades
    if datos.hitos is not None:
        # Sella cada hito con fecha+hora la primera vez y conserva el sello original
        # después: el historial de etapas (con sus archivos) se preserva SIEMPRE.
        prev = seg.hitos or {}
        ahora = datetime.now(timezone.utc).isoformat()
        nuevos: dict = {}
        for k, v in datos.hitos.items():
            d = v.model_dump()
            d.pop("ts", None)  # el sello lo maneja el servidor, no el cliente
            d["ts"] = (prev.get(k) or {}).get("ts") or ahora
            nuevos[k] = d
        # La etapa actual siempre queda registrada, aunque no se haya cargado
        # fecha/nota/archivo, para que el historial muestre cuándo se alcanzó.
        if datos.estado not in nuevos:
            nuevos[datos.estado] = {
                "fecha": None,
                "nota": None,
                "adjuntos": None,
                "ts": (prev.get(datos.estado) or {}).get("ts") or ahora,
            }
        seg.hitos = nuevos

    # Información de envío: solo Marcela (admin). La vendedora conserva lo cargado.
    if not es_vendedora:
        # De "en tránsito" en adelante el contenedor ya está despachado.
        en_transito_o_mas = ESTADOS_ENVIO.index(datos.estado) >= ESTADOS_ENVIO.index("en_transito")

        # El monto de la venta (USD) es obligatorio para despachar. Se conserva el
        # ya guardado si esta edición no lo reenvía.
        monto_final = datos.monto_venta if datos.monto_venta is not None else seg.monto_venta
        if en_transito_o_mas and (monto_final is None or monto_final <= 0):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Ingresa el monto de la venta (USD) para marcar el pedido en tránsito",
            )

        seg.numero_tracking = datos.numero_tracking
        seg.naviera = datos.naviera
        seg.url_tracking = datos.url_tracking
        seg.fecha_eta = datos.fecha_eta
        seg.bl_numero = datos.bl_numero
        seg.bl_pdf_url = datos.bl_pdf_url
        if datos.monto_venta is not None:
            seg.monto_venta = datos.monto_venta

        # Sella el despacho la primera vez que el pedido entra a "en tránsito".
        if en_transito_o_mas and seg.despachado_at is None:
            seg.despachado_at = datetime.now(timezone.utc)

    numero = f"YUDA-{sesion.fecha:%Y%m%d}-{sesion.id[:6].upper()}"

    # Aviso a Marcela cuando la cotización llega a "en bodega" (lista para envío)
    if datos.estado == ESTADO_DISPARA_AVISO and estado_anterior != ESTADO_DISPARA_AVISO:
        avisar_listo_para_envio(db, sesion_id, numero, sesion.nombre_cliente, sesion.user_id)

    # Aviso a la vendedora dueña cuando Marcela despacha o entrega su cotización
    if datos.estado in ("en_transito", "entregado") and datos.estado != estado_anterior:
        avisar_envio_a_vendedora(
            db, sesion_id, numero, sesion.nombre_cliente, sesion.user_id, datos.estado
        )

    db.commit()
    db.refresh(seg)
    return seg


@router.post("/sesiones/{sesion_id}/seguimiento/bl-pdf")
async def subir_bl_pdf(
    sesion_id: str,
    archivo: UploadFile,
    usuario: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    """Sube el PDF del BL (solo Marcela) y devuelve su URL para guardarla en el seguimiento"""
    _sesion_autorizada(db, sesion_id, usuario)

    if archivo.content_type != "application/pdf":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El BL debe ser un archivo PDF")

    contenido = await archivo.read()
    if len(contenido) > 25 * 1024 * 1024:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El PDF no debe superar 25MB")

    nombre_archivo = f"bl/{sesion_id}-{uuid.uuid4().hex[:8]}.pdf"
    loop = asyncio.get_event_loop()
    url = await loop.run_in_executor(None, lambda: subir_pdf(contenido, nombre_archivo))
    return {"url": url}


# Tipos de imagen permitidos como adjunto de una etapa
_IMG_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


@router.post("/sesiones/{sesion_id}/seguimiento/adjunto")
async def subir_adjunto_seguimiento(
    sesion_id: str,
    archivo: UploadFile,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> dict:
    """Sube un PDF o imagen para adjuntarlo a una etapa del seguimiento.

    Lo puede subir la vendedora (en sus etapas) o Marcela; el cliente lo verá en
    su portal dentro del tracking. Devuelve {url, nombre, tipo} para guardarlo en
    el hito correspondiente.
    """
    _sesion_autorizada(db, sesion_id, usuario)

    if archivo.content_type == "application/pdf":
        tipo, extension = "pdf", ".pdf"
    elif archivo.content_type in _IMG_EXT:
        tipo, extension = "imagen", _IMG_EXT[archivo.content_type]
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Solo se permiten archivos PDF o imágenes (JPG, PNG, WEBP)"
        )

    contenido = await archivo.read()
    if len(contenido) > 25 * 1024 * 1024:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El archivo no debe superar 25MB")

    nombre_archivo = f"seguimiento/{sesion_id}-{uuid.uuid4().hex[:8]}{extension}"
    loop = asyncio.get_event_loop()
    if tipo == "pdf":
        url = await loop.run_in_executor(None, lambda: subir_pdf(contenido, nombre_archivo))
    else:
        url = await loop.run_in_executor(
            None, lambda: subir_foto(contenido, nombre_archivo, archivo.content_type)
        )
    return {"url": url, "nombre": archivo.filename, "tipo": tipo}


# ---------------------------------------------------------------------------
# Cuentas de clientes (estado de cuenta / ledger). Gestión: admin y contadora.
# Lectura: además la vendedora dueña del cliente.
# ---------------------------------------------------------------------------


def _estado_cuenta(db: Session, cliente: Cliente) -> dict:
    movimientos = (
        db.query(MovimientoCuenta).filter(MovimientoCuenta.cliente_id == cliente.id).all()
    )
    # Pedidos = cotizaciones del cliente (para el nombre/fecha de cada apartado).
    sesiones = db.query(Sesion).filter(Sesion.cliente_id == cliente.id).all()
    return construir_estado_cuenta(cliente, movimientos, sesiones)


def _validar_sesion_del_cliente(db: Session, cliente_id: str, sesion_id: str | None) -> None:
    """El pedido (cotización) asociado a un movimiento debe ser del propio cliente."""
    if sesion_id is None:
        return
    existe = (
        db.query(Sesion)
        .filter(Sesion.id == sesion_id, Sesion.cliente_id == cliente_id)
        .first()
    )
    if existe is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "El pedido no pertenece a este cliente"
        )


def _validar_moneda_pedido(
    db: Session, cliente_id: str, sesion_id: str | None, moneda: str, excluir_id: str | None = None
) -> None:
    """Todos los movimientos de un mismo pedido deben usar la misma moneda."""
    if sesion_id is None:
        return
    q = db.query(MovimientoCuenta).filter(
        MovimientoCuenta.cliente_id == cliente_id,
        MovimientoCuenta.sesion_id == sesion_id,
    )
    if excluir_id:
        q = q.filter(MovimientoCuenta.id != excluir_id)
    otro = q.first()
    if otro is not None and (otro.moneda or "USD") != moneda:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Este pedido ya usa la moneda {otro.moneda}. Usa la misma moneda para el pedido.",
        )


@router.get("/clientes/{cliente_id}/cuenta", response_model=EstadoCuentaResponse)
def obtener_estado_cuenta(
    cliente_id: str,
    usuario: User = Depends(require_roles("admin", "contadora", "vendedora")),
    db: Session = Depends(get_db),
) -> dict:
    """Estado de cuenta del cliente (compras, comisión, abonos, saldo + ledger)"""
    cliente = _cliente_autorizado(db, cliente_id, usuario)
    return _estado_cuenta(db, cliente)


@router.post(
    "/clientes/{cliente_id}/movimientos",
    response_model=EstadoCuentaResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_movimiento(
    cliente_id: str,
    datos: MovimientoCreate,
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> dict:
    """Agrega un movimiento (envío) a la cuenta del cliente y devuelve la cuenta"""
    cliente = _cliente_autorizado(db, cliente_id, usuario)
    _validar_sesion_del_cliente(db, cliente.id, datos.sesion_id)
    _validar_moneda_pedido(db, cliente.id, datos.sesion_id, datos.moneda)
    comision = (
        datos.comision_yuda
        if datos.comision_yuda is not None
        else calcular_comision(datos.valor_mercancia)
    )
    movimiento = MovimientoCuenta(
        cliente_id=cliente.id,
        sesion_id=datos.sesion_id,
        contenedor_id=datos.contenedor_id,
        moneda=datos.moneda,
        envio=datos.envio,
        fecha=datos.fecha,
        guia=datos.guia,
        descripcion=datos.descripcion,
        valor_mercancia=datos.valor_mercancia,
        comision_yuda=comision,
        abono=datos.abono,
        nota=datos.nota,
    )
    db.add(movimiento)
    db.commit()
    return _estado_cuenta(db, cliente)


@router.patch(
    "/clientes/{cliente_id}/movimientos/{movimiento_id}",
    response_model=EstadoCuentaResponse,
)
def actualizar_movimiento(
    cliente_id: str,
    movimiento_id: str,
    datos: MovimientoUpdate,
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> dict:
    """Actualiza un movimiento de la cuenta (campos omitidos no cambian)"""
    cliente = _cliente_autorizado(db, cliente_id, usuario)
    movimiento = (
        db.query(MovimientoCuenta)
        .filter(
            MovimientoCuenta.id == movimiento_id,
            MovimientoCuenta.cliente_id == cliente.id,
        )
        .first()
    )
    if movimiento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Movimiento no encontrado")

    cambios = datos.model_dump(exclude_unset=True)
    # Si se reasigna el pedido, validar que sea del mismo cliente.
    if "sesion_id" in cambios:
        _validar_sesion_del_cliente(db, cliente.id, cambios["sesion_id"])
    # La moneda debe seguir siendo consistente con el pedido tras el cambio.
    if "moneda" in cambios or "sesion_id" in cambios:
        nueva_sesion = cambios.get("sesion_id", movimiento.sesion_id)
        nueva_moneda = cambios.get("moneda", movimiento.moneda or "USD")
        _validar_moneda_pedido(db, cliente.id, nueva_sesion, nueva_moneda, excluir_id=movimiento.id)
    # Si cambió el valor y NO se envió comisión explícita, recalcular la comisión.
    if "valor_mercancia" in cambios and "comision_yuda" not in cambios:
        cambios["comision_yuda"] = calcular_comision(cambios["valor_mercancia"])
    for campo, valor in cambios.items():
        setattr(movimiento, campo, valor)
    db.commit()
    return _estado_cuenta(db, cliente)


@router.delete(
    "/clientes/{cliente_id}/movimientos/{movimiento_id}",
    response_model=EstadoCuentaResponse,
)
def eliminar_movimiento(
    cliente_id: str,
    movimiento_id: str,
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> dict:
    """Elimina un movimiento de la cuenta del cliente"""
    cliente = _cliente_autorizado(db, cliente_id, usuario)
    movimiento = (
        db.query(MovimientoCuenta)
        .filter(
            MovimientoCuenta.id == movimiento_id,
            MovimientoCuenta.cliente_id == cliente.id,
        )
        .first()
    )
    if movimiento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Movimiento no encontrado")
    db.delete(movimiento)
    db.commit()
    return _estado_cuenta(db, cliente)
