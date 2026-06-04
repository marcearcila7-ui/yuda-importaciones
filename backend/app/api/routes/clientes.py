import secrets
import string
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.database import get_db
from app.models.cliente import Cliente
from app.models.seguimiento import ESTADO_INICIAL, SeguimientoPedido
from app.models.sesion import Sesion
from app.models.user import User
from app.schemas.cliente import (
    ClienteCreado,
    ClienteCreate,
    ClienteResponse,
    ClienteUpdate,
    ResetPasswordRequest,
)
from app.schemas.packing import SesionResponse
from app.schemas.seguimiento import SeguimientoResponse, SeguimientoUpdate
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
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> list[Cliente]:
    """Lista clientes: la vendedora ve los suyos, el admin ve todos."""
    query = db.query(Cliente)
    if usuario.rol.value == "vendedora":
        query = query.filter(Cliente.vendedora_id == usuario.id)
    return query.order_by(Cliente.created_at.desc()).all()


@router.get("/clientes/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente(
    cliente_id: str,
    usuario: User = Depends(require_roles("admin", "vendedora")),
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
        seg = SeguimientoPedido(
            sesion_id=sesion_id,
            estado=ESTADO_INICIAL,
            hitos={ESTADO_INICIAL: {"fecha": datetime.now().date().isoformat(), "nota": None}},
        )
        db.add(seg)

    db.commit()
    db.refresh(seg)
    return seg


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
    """Crea o actualiza el seguimiento del envío de una cotización"""
    _sesion_autorizada(db, sesion_id, usuario)

    seg = db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == sesion_id).first()
    if seg is None:
        seg = SeguimientoPedido(sesion_id=sesion_id)
        db.add(seg)

    seg.estado = datos.estado
    seg.novedades = datos.novedades
    seg.numero_tracking = datos.numero_tracking
    seg.naviera = datos.naviera
    seg.url_tracking = datos.url_tracking
    seg.fecha_eta = datos.fecha_eta
    if datos.hitos is not None:
        seg.hitos = {k: v.model_dump() for k, v in datos.hitos.items()}

    db.commit()
    db.refresh(seg)
    return seg
