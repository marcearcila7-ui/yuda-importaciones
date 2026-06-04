from pydantic import field_validator
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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator(
        "DATABASE_URL",
        "SECRET_KEY",
        "ANTHROPIC_API_KEY",
        "CORS_ORIGINS",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
        mode="before",
    )
    @classmethod
    def _limpiar_espacios(cls, v):
        """Limpia espacios accidentales al pegar valores en variables de entorno"""
        return v.strip() if isinstance(v, str) else v

    @property
    def cors_origins_list(self) -> list[str]:
        """Convierte la cadena separada por comas en una lista de orígenes"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


# Instancia global de configuración usada en toda la aplicación
settings = Settings()
