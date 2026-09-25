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

    # Yuda Contable (app aparte, base de datos separada): solo para heredar
    # el teléfono/WhatsApp del cliente por "sigla" (la misma que Marcela ya
    # escribe a mano para cruzar el cliente entre las dos apps). Si quedan
    # vacías, simplemente no hay dato de contacto que heredar -no rompe nada.
    CONTABLE_SUPABASE_URL: str = ""
    CONTABLE_SUPABASE_SERVICE_KEY: str = ""

    # Yuda Contable, API interna (su propia app, no la base de datos directo):
    # búsqueda de clientes en vivo, estado de cuenta y el PDF oficial. Token
    # propio (INTERNAL_API_TOKEN allá), distinto del de arriba. Si quedan
    # vacías, esas funciones simplemente no responden -no rompe nada.
    YUDA_CONTABLE_BASE_URL: str = ""
    YUDA_CONTABLE_API_TOKEN: str = ""

    # Avisos al cliente (portal): correo transaccional por Brevo y notificación
    # por el bot propio de Yuda. Ambos son opcionales; si faltan, el aviso
    # correspondiente simplemente se omite (no rompe el flujo de bodega/Marcela).
    BREVO_API_KEY: str = ""
    BREVO_SENDER_EMAIL: str = ""
    BREVO_SENDER_NAME: str = "YUDA Importaciones"
    # WhatsApp por Lucid Bot (construido sobre ChatRace: api.chatrace.com).
    # Se autentica con el header X-ACCESS-TOKEN.
    LUCIDBOT_API_KEY: str = ""
    LUCIDBOT_API_URL: str = "https://api.chatrace.com"
    # Fuera de la ventana de 24h de conversación, WhatsApp exige una plantilla
    # aprobada en vez de texto libre. Si se deja vacío, se manda texto libre
    # (solo funciona dentro de esa ventana). Si se define, se dispara ese flow
    # de Lucid Bot (la plantilla vive ahí) pasándole las variables por custom
    # fields del contacto antes de dispararlo.
    LUCIDBOT_FLOW_APROBAR_DESPACHO: str = ""
    # Mismo mecanismo que el de arriba, para los otros dos avisos automáticos
    # al cliente (fuera de la ventana de 24h necesitan su propia plantilla).
    LUCIDBOT_FLOW_COTIZACION_ENVIADA: str = ""
    LUCIDBOT_FLOW_PEDIDO_ENVIADO: str = ""
    LUCIDBOT_FLOW_FECHA_TENTATIVA: str = ""
    LUCIDBOT_FLOW_DESPACHADO: str = ""
    LUCIDBOT_FLOW_EN_DESTINO: str = ""
    LUCIDBOT_FLOW_ENTREGADO: str = ""
    # Nombres (no IDs) de los custom fields de Lucid Bot donde se dejan las
    # variables antes de disparar el flow de arriba. Deben existir ya creados
    # en Lucid Bot con exactamente estos nombres (o cambiar acá para que
    # coincidan con los tuyos).
    LUCIDBOT_CF_NUMERO_PEDIDO: str = "yuda_numero_pedido"
    LUCIDBOT_CF_PLAZO: str = "yuda_plazo_aprobacion"
    LUCIDBOT_CF_LINK: str = "yuda_link_portal"
    LUCIDBOT_CF_NOTA: str = "yuda_nota_bodega"
    LUCIDBOT_CF_FECHA_TENTATIVA: str = "yuda_fecha_tentativa"
    LUCIDBOT_CF_NAVIERA: str = "yuda_naviera"
    LUCIDBOT_CF_TRACKING: str = "yuda_tracking"
    LUCIDBOT_CF_ETA: str = "yuda_eta"
    # Base pública del portal del cliente, para armar el link en los avisos.
    PORTAL_URL: str = "http://localhost:3000"

    # Notificaciones push (avisos aunque el navegador esté cerrado): llaves
    # VAPID propias de YUDA. La privada va en base64 porque un PEM con saltos
    # de línea no siempre sobrevive intacto como variable de entorno. Si
    # quedan vacías, el envío de push simplemente se omite (no rompe nada).
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY_B64: str = ""
    VAPID_CLAIMS_EMAIL: str = "mailto:soporte@yudaimportaciones.com"

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
        "CONTABLE_SUPABASE_URL",
        "CONTABLE_SUPABASE_SERVICE_KEY",
        "YUDA_CONTABLE_BASE_URL",
        "YUDA_CONTABLE_API_TOKEN",
        "SENTRY_DSN",
        "BREVO_API_KEY",
        "LUCIDBOT_API_KEY",
        "LUCIDBOT_API_URL",
        "PORTAL_URL",
        "VAPID_PUBLIC_KEY",
        "VAPID_PRIVATE_KEY_B64",
        "VAPID_CLAIMS_EMAIL",
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
