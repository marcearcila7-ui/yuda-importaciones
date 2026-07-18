"""Infraestructura de tests: app con base SQLite en memoria y TestClient.

Se definen las variables de entorno mínimas ANTES de importar la app (config las
exige al importar). La base de producción (Postgres) no se toca: se sobreescribe
la dependencia get_db con sesiones a un SQLite en memoria.
"""
import os

os.environ.setdefault("SECRET_KEY", "x" * 40)
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost/db")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.main  # noqa: E402  (registra todos los modelos en Base.metadata)
from app.core.security import hash_password  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.cliente import Cliente  # noqa: E402
from app.models.item import Item  # noqa: E402
from app.models.seguimiento import ESTADO_INICIAL, SeguimientoPedido  # noqa: E402
from app.models.sesion import Sesion  # noqa: E402
from app.models.user import RolUsuario, User  # noqa: E402

# Una única conexión SQLite en memoria compartida (StaticPool) para que los datos
# persistan entre la sesión del test y las de los requests.
_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_Session = sessionmaker(bind=_engine, autoflush=False, autocommit=False)

PASS = "Clave1234!"


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=_engine)
    s = _Session()
    try:
        yield s
    finally:
        s.close()
        Base.metadata.drop_all(bind=_engine)


@pytest.fixture()
def client(db):
    def _get_db():
        s = _Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _get_db
    # Reinicia el limitador de intentos entre tests (estado en memoria del proceso).
    import app.core.rate_limit as rl

    rl._intentos.clear()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ─────────── helpers de seed ───────────


@pytest.fixture()
def crear_usuario(db):
    def _crear(email, rol=RolUsuario.vendedora, nombre="Test", activo=True):
        u = User(
            email=email,
            nombre=nombre,
            rol=rol,
            hashed_password=hash_password(PASS),
            activo=activo,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        return u

    return _crear


@pytest.fixture()
def crear_cliente(db):
    def _crear(email, vendedora_id, nombre="Cliente", activo=True):
        c = Cliente(
            email=email,
            nombre=nombre,
            hashed_password=hash_password(PASS),
            vendedora_id=vendedora_id,
            activo=activo,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        return c

    return _crear


@pytest.fixture()
def crear_sesion(db):
    from datetime import date

    def _crear(user_id, cliente_id=None, enviada=False, con_item=True):
        s = Sesion(
            nombre_cliente="Cliente",
            fecha=date(2026, 1, 1),
            user_id=user_id,
            cliente_id=cliente_id,
            enviada_cliente=enviada,
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        if enviada:
            db.add(SeguimientoPedido(sesion_id=s.id, estado=ESTADO_INICIAL))
        if con_item:
            db.add(
                Item(
                    sesion_id=s.id,
                    supplier_nombre="Prov",
                    descripcion_es="Producto",
                    ctns=5,
                    qty_por_ctn=10,
                    price_rmb=2.0,
                    orden=1,
                )
            )
        db.commit()
        db.refresh(s)
        return s

    return _crear


@pytest.fixture()
def token_staff(client):
    def _token(email, password=PASS):
        r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        return r.json()["access_token"]

    return _token


@pytest.fixture()
def token_portal(client):
    def _token(email, password=PASS):
        r = client.post("/api/v1/portal/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        return r.json()["access_token"]

    return _token
