from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.rate_limit import esta_bloqueado, ip_del_request, limpiar, registrar_fallo
from app.core.security import create_access_token, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UsuarioResponse

router = APIRouter(prefix="/auth", tags=["auth"])

# Anti fuerza bruta: máximos intentos fallidos por ventana (15 min).
_VENTANA = 15 * 60
_MAX_POR_EMAIL = 5
_MAX_POR_IP = 20


@router.post("/login", response_model=TokenResponse)
def login(datos: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    """Valida credenciales y devuelve un JWT junto con los datos del usuario"""
    clave_email = f"staff:email:{datos.email.lower()}"
    clave_ip = f"staff:ip:{ip_del_request(request)}"
    if esta_bloqueado(clave_email, _MAX_POR_EMAIL, _VENTANA) or esta_bloqueado(
        clave_ip, _MAX_POR_IP, _VENTANA
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos fallidos. Esperá unos minutos e intentá de nuevo.",
        )

    user = db.query(User).filter(User.email == datos.email).first()

    # Usuario inexistente o contraseña incorrecta
    if user is None or not verify_password(datos.password, user.hashed_password):
        registrar_fallo(clave_email, _VENTANA)
        registrar_fallo(clave_ip, _VENTANA)
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

    # Login exitoso: limpia el contador de intentos de ese email.
    limpiar(clave_email)

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
