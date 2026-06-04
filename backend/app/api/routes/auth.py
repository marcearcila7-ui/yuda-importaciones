from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.security import create_access_token, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UsuarioResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(datos: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Valida credenciales y devuelve un JWT junto con los datos del usuario"""
    user = db.query(User).filter(User.email == datos.email).first()

    # Usuario inexistente o contraseña incorrecta
    if user is None or not verify_password(datos.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    # Usuario desactivado
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )

    # El payload del token lleva email (sub), id y rol
    token = create_access_token(
        {"sub": user.email, "user_id": user.id, "rol": user.rol.value, "tipo": "staff"}
    )

    return TokenResponse(
        access_token=token,
        usuario=UsuarioResponse(
            id=user.id,
            nombre=user.nombre,
            email=user.email,
            rol=user.rol.value,
        ),
    )


@router.get("/me", response_model=UsuarioResponse)
def me(user: User = Depends(get_current_user)) -> UsuarioResponse:
    """Devuelve los datos del usuario autenticado a partir del token"""
    return UsuarioResponse(
        id=user.id,
        nombre=user.nombre,
        email=user.email,
        rol=user.rol.value,
    )
