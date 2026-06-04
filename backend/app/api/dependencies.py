from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import verify_token
from app.database import get_db
from app.models.cliente import Cliente
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

    return cliente


def require_roles(*roles: str):
    """Genera una dependencia que exige que el usuario tenga uno de los roles dados"""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.rol.value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sin permisos para esta acción",
            )
        return user

    return dependency
