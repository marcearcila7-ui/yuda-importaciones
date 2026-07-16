import pytest
from pydantic import ValidationError

from app.core.config import Settings

_DB = "postgresql://u:p@localhost/db"


def test_config_valida():
    s = Settings(SECRET_KEY="x" * 40, DATABASE_URL=_DB)
    assert len(s.SECRET_KEY) == 40


def test_secret_key_vacia_falla():
    with pytest.raises(ValidationError):
        Settings(SECRET_KEY="", DATABASE_URL=_DB)


def test_secret_key_corta_falla():
    with pytest.raises(ValidationError):
        Settings(SECRET_KEY="corta", DATABASE_URL=_DB)


def test_database_url_vacia_falla():
    with pytest.raises(ValidationError):
        Settings(SECRET_KEY="x" * 40, DATABASE_URL="")
