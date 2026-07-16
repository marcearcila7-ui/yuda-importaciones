from datetime import datetime, timedelta, timezone

from jose import jwt

from app.core.config import settings
from app.core.security import (
    ALGORITHM,
    create_access_token,
    hash_password,
    verify_password,
    verify_token,
)


def test_hash_password_roundtrip():
    hashed = hash_password("secreta123")
    assert hashed != "secreta123"
    assert verify_password("secreta123", hashed)
    assert not verify_password("otra", hashed)


def test_token_roundtrip():
    token = create_access_token({"sub": "u1", "tipo": "staff"})
    payload = verify_token(token)
    assert payload is not None
    assert payload["sub"] == "u1"
    assert payload["tipo"] == "staff"


def test_token_alterado_se_rechaza():
    token = create_access_token({"sub": "u1"})
    tocado = token[:-1] + ("a" if token[-1] != "a" else "b")
    assert verify_token(tocado) is None


def test_token_vencido_se_rechaza():
    vencido = jwt.encode(
        {"sub": "u1", "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    assert verify_token(vencido) is None
