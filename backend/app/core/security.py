from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Contexto de cifrado para contraseñas usando bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Algoritmo de firma para los JWT
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Genera el hash bcrypt de una contraseña en texto plano"""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica una contraseña en texto plano contra su hash"""
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    """Crea un JWT con los datos recibidos más el campo de expiración (exp)"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict | None:
    """Decodifica y valida un JWT. Retorna el payload o None si es inválido/expirado"""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
