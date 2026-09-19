from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import verify_token
from app.database import get_db
from app.models.cliente import Cliente
from app.models.cliente_vendedora import ClienteVendedora
from app.models.sesion import Sesion
from app.models.user import User

# Esquema OAuth2 que extrae el token del header Authorization: Bearer.
# auto_error=False para que el mensaje 401 sea siempre en español.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Obtiene el usuario (staff) autenticado a partir del token; lanza 401 si falla"""
    no_autenticado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado",
    )

    # Sin header Authorization, token llega como None
    if token is None:
        raise no_autenticado

    payload = verify_token(token)
    if payload is None:
        raise no_autenticado

    # Un token del portal de clientes no sirve para el área del equipo
    if payload.get("tipo") == "cliente":
        raise no_autenticado

    email = payload.get("sub")
    if not email:
        raise no_autenticado

    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.activo:
        raise no_autenticado

    # Revocación: si el token trae 'tv' y no coincide con la versión actual del
    # usuario, fue invalidado (p. ej. tras un reset de contraseña). Los tokens
    # viejos sin 'tv' se aceptan hasta que expiren (compatibilidad).
    tv = payload.get("tv")
    if tv is not None and tv != user.token_version:
        raise no_autenticado

    return user


def get_current_cliente(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Cliente:
    """Obtiene el cliente autenticado del portal a partir del token; lanza 401 si falla"""
    no_autenticado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado",
    )

    if token is None:
        raise no_autenticado

    payload = verify_token(token)
    if payload is None or payload.get("tipo") != "cliente":
        raise no_autenticado

    cliente_id = payload.get("sub")
    if not cliente_id:
        raise no_autenticado

    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if cliente is None or not cliente.activo:
        raise no_autenticado

    # Revocación (ver get_current_user).
    tv = payload.get("tv")
    if tv is not None and tv != cliente.token_version:
        raise no_autenticado

    return cliente


def exigir_roles(usuario: User, *roles: str) -> None:
    """Lanza 403 si el rol del usuario no está entre los permitidos (uso imperativo,
    dentro del cuerpo de un endpoint). Es la contraparte de `require_roles`."""
    if usuario.rol.value not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sin permisos para esta acción",
        )


def vendedora_tiene_acceso_cliente(db: Session, cliente_id: str, vendedora_id: str) -> bool:
    """¿Marcela le compartió este cliente a esta vendedora (además de su
    posible dueña, que se revisa aparte)? Fase 1: clientes compartidos."""
    return (
        db.query(ClienteVendedora.id)
        .filter(ClienteVendedora.cliente_id == cliente_id, ClienteVendedora.vendedora_id == vendedora_id)
        .first()
        is not None
    )


def exigir_acceso_sesion(db: Session, sesion: Sesion, usuario: User) -> None:
    """Lanza 403 si una vendedora no puede gestionar esta cotización: ni la
    creó, ni es dueña o colaboradora del cliente al que está vinculada.

    Punto único para este chequeo: antes vivía duplicado (con la misma
    lógica, pero sin enterarse de clientes compartidos) en clientes.py,
    pedidos.py, packing.py y lotes.py — una vendedora agregada como
    colaboradora de un cliente podía ver sus cotizaciones, pero cualquier
    acción puntual (seguimiento, packing, OCR, generar pedidos) le daba 403.
    """
    if usuario.rol.value != "vendedora" or sesion.user_id == usuario.id:
        return
    if sesion.cliente_id:
        cliente = db.query(Cliente).filter(Cliente.id == sesion.cliente_id).first()
        if cliente is not None and (
            cliente.vendedora_id == usuario.id
            or vendedora_tiene_acceso_cliente(db, sesion.cliente_id, usuario.id)
        ):
            return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin permisos sobre esta cotización")


def require_roles(*roles: str):
    """Genera una dependencia que exige que el usuario tenga uno de los roles dados"""

    def dependency(user: User = Depends(get_current_user)) -> User:
        exigir_roles(user, *roles)
        return user

    return dependency
