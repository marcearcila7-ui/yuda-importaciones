from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación leída desde variables de entorno y .env"""

    DATABASE_URL: str = ""
    SECRET_KEY: str = ""
    TIPO_CAMBIO_USD: float = 6.7
    ANTHROPIC_API_KEY: str = ""
    UPLOAD_DIR: str = "./uploads"
    CORS_ORIGINS: str = "http://localhost:3000"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 8
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # Tope GLOBAL de llamadas de OCR (Anthropic) en simultáneo en todo el sistema.
    # Protege contra rate limits y agotamiento de conexiones bajo picos de carga.
    OCR_CONCURRENCIA_GLOBAL: int = 6
    # Fotos en paralelo dentro de un mismo lote (acota memoria/descargas por job).
    OCR_CONCURRENCIA_LOTE: int = 4
    # Reintentos automáticos con backoff del SDK de Anthropic ante 429/errores transitorios.
    OCR_MAX_RETRIES: int = 4
    # Pool de conexiones a la base de datos (total máx = POOL_SIZE + MAX_OVERFLOW).
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Cola con worker aparte. Si es True, el OCR de los lotes NO corre en el proceso
    # web: se encola en la base y lo procesa un servicio worker separado
    # (python -m app.worker). Default False = comportamiento anterior (OCR en el web).
    USE_WORKER: bool = False
    # Cada cuánto el worker consulta la cola cuando está ocioso.
    WORKER_POLL_SECONDS: int = 3

    # Nivel de logging (DEBUG, INFO, WARNING, ERROR).
    LOG_LEVEL: str = "INFO"

    # Monitoreo de errores (Sentry). Si SENTRY_DSN está vacío, Sentry NO se inicia
    # (comportamiento por defecto en local y tests). En producción, pon el DSN del
    # proyecto para recibir el stack trace de cada error al instante.
    SENTRY_DSN: str = ""
    # Etiqueta el entorno en Sentry (production / staging / etc.).
    SENTRY_ENVIRONMENT: str = "production"
    # Muestreo de trazas de performance (0.0 = solo errores, sin costo de tracing).
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator(
        "DATABASE_URL",
        "SECRET_KEY",
        "ANTHROPIC_API_KEY",
        "CORS_ORIGINS",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
        "SENTRY_DSN",
        mode="before",
    )
    @classmethod
    def _limpiar_espacios(cls, v):
        """Limpia espacios accidentales al pegar valores en variables de entorno"""
        return v.strip() if isinstance(v, str) else v

    @model_validator(mode="after")
    def _validar_secretos_obligatorios(self):
        """Falla el arranque si faltan secretos críticos, en vez de arrancar en un
        estado inseguro. Con SECRET_KEY vacía los JWT se firmarían con "" y serían
        falsificables; sin DATABASE_URL la app no puede operar."""
        if not self.SECRET_KEY:
            raise ValueError(
                "SECRET_KEY es obligatoria y está vacía. Definí una cadena aleatoria "
                "de al menos 32 caracteres en el entorno/.env antes de arrancar."
            )
        if len(self.SECRET_KEY) < 32:
            raise ValueError(
                f"SECRET_KEY es demasiado corta ({len(self.SECRET_KEY)} caracteres); "
                "usa al menos 32 caracteres aleatorios."
            )
        if not self.DATABASE_URL:
            raise ValueError(
                "DATABASE_URL es obligatoria y está vacía. Configurá la conexión a "
                "Postgres en el entorno/.env antes de arrancar."
            )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        """Convierte la cadena separada por comas en una lista de orígenes"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


# Instancia global de configuración usada en toda la aplicación
settings = Settings()
