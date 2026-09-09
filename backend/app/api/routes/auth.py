import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.rate_limit import esta_bloqueado, ip_del_request, limpiar, registrar_fallo
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MensajeResponse,
    OlvidePasswordRequest,
    ResetPasswordRequest,
    TokenResponse,
    UsuarioResponse,
)
from app.services.email_service import enviar_recuperacion

router = APIRouter(prefix="/auth", tags=["auth"])

# Anti fuerza bruta: máximos intentos fallidos por ventana (15 min).
_VENTANA = 15 * 60
_MAX_POR_EMAIL = 5
_MAX_POR_IP = 20

# El token de recuperación vence rápido: es un acceso directo a cambiar la
# contraseña, no una sesión normal.
_RESET_VENCE_HORAS = 1


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


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
            detail="Demasiados intentos fallidos. Espera unos minutos e intenta de nuevo.",
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
        {
            "sub": user.email,
            "user_id": user.id,
            "rol": user.rol.value,
            "tipo": "staff",
            "tv": user.token_version,
        }
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


# Mismo mensaje para cualquier resultado: si el correo existe o no, la
# respuesta es idéntica, para no dejar tantear qué emails están registrados.
_MENSAJE_OLVIDE = MensajeResponse(
    mensaje="Si el correo está registrado, te llegará un enlace para elegir una contraseña nueva."
)


@router.post("/olvide-password", response_model=MensajeResponse)
async def olvide_password(
    datos: OlvidePasswordRequest, request: Request, db: Session = Depends(get_db)
) -> MensajeResponse:
    """Pide recuperar la contraseña: si el correo existe, manda el enlace"""
    clave_email = f"reset:email:{datos.email.lower()}"
    clave_ip = f"reset:ip:{ip_del_request(request)}"
    if esta_bloqueado(clave_email, _MAX_POR_EMAIL, _VENTANA) or esta_bloqueado(
        clave_ip, _MAX_POR_IP, _VENTANA
    ):
        # Mismo mensaje genérico: ni el bloqueo se nota desde afuera.
        return _MENSAJE_OLVIDE
    registrar_fallo(clave_email, _VENTANA)
    registrar_fallo(clave_ip, _VENTANA)

    user = db.query(User).filter(User.email == datos.email, User.activo).first()
    if user is not None:
        token = secrets.token_urlsafe(32)
        user.reset_token_hash = _hash_token(token)
        user.reset_token_expira = datetime.now(timezone.utc) + timedelta(hours=_RESET_VENCE_HORAS)
        db.commit()
        link = f"{settings.frontend_url}/reset-password?token={token}"
        await enviar_recuperacion(user.email, user.nombre, link)

    return _MENSAJE_OLVIDE


@router.post("/reset-password", response_model=MensajeResponse)
def reset_password(datos: ResetPasswordRequest, db: Session = Depends(get_db)) -> MensajeResponse:
    """Cambia la contraseña con el token que llegó por correo"""
    if len(datos.nueva_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña nueva debe tener al menos 8 caracteres",
        )
    hash_recibido = _hash_token(datos.token)
    user = db.query(User).filter(User.reset_token_hash == hash_recibido).first()
    ahora = datetime.now(timezone.utc)
    if user is None or user.reset_token_expira is None or user.reset_token_expira < ahora:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este enlace ya no es válido. Pide uno nuevo desde \"Olvidé mi contraseña\".",
        )

    user.hashed_password = hash_password(datos.nueva_password)
    user.reset_token_hash = None
    user.reset_token_expira = None
    # Cierra sesión en cualquier otro dispositivo donde hubiera quedado logueada.
    user.token_version += 1
    db.commit()

    return MensajeResponse(mensaje="Contraseña actualizada. Ya puedes ingresar con la nueva.")
