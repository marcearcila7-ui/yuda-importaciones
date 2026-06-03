from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# Motor de conexión a PostgreSQL
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# Fábrica de sesiones para interactuar con la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Clase base declarativa para todos los modelos (SQLAlchemy 2.0)"""

    pass


def get_db() -> Generator[Session, None, None]:
    """Generador de sesión para inyección de dependencias en FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
