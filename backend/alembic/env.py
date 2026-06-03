import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Importa Base y todos los modelos para que autogenerate los detecte
from app.database import Base
import app.models  # noqa: F401

# Objeto de configuración de Alembic
config = context.config

# Toma la URL de conexión desde la variable de entorno DATABASE_URL
config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

# Configuración de logging desde el archivo .ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadatos objetivo para autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Ejecuta las migraciones en modo 'offline' (sin conexión)"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta las migraciones en modo 'online' (con conexión)"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
