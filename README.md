# YUDA Importaciones

Sistema de cotización y compras para una empresa de importación desde China.
Las vendedoras fotografían etiquetas de proveedores en el mercado de Yiwu, el OCR
extrae los datos, se arma el Packing List por cliente y se generan los pedidos por proveedor.

## Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Frontend | React 18 + Vite + TypeScript + Tailwind CSS v3 |
| Backend | Python 3.11 + FastAPI + SQLAlchemy 2.0 + Alembic |
| Base de datos | PostgreSQL 15 |
| OCR / IA | Claude Vision (SDK anthropic) |
| Contenedores | Docker Compose v2 |

## Requisitos previos

- Docker y Docker Compose v2
- git

## Levantamiento local

```bash
# 1. Clonar el repositorio
git clone <repo> && cd yuda

# 2. Crear el archivo de entorno de desarrollo
cp .env.example .env
# Completar DATABASE_URL, SECRET_KEY y ANTHROPIC_API_KEY en .env

# 3. Levantar todo
docker compose up --build

# 4. Aplicar migraciones (primera vez)
docker compose exec backend alembic upgrade head

# 5. Cargar los usuarios iniciales
docker compose exec backend python seed.py
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000 (Swagger en `/docs`)

## Deploy en producción

Backend + DB corren en un servidor con Docker Compose; el frontend puede ir en
Vercel o en el mismo servidor (nginx).

```bash
# En el servidor, dentro del repo:
cp .env.prod.example .env.prod
# Completar TODOS los valores de .env.prod (ver tabla de variables)

chmod +x deploy.sh
./deploy.sh
```

`deploy.sh` hace: pull del código, build de las imágenes de producción
(`docker-compose.prod.yml`), espera al backend, corre las migraciones y verifica el health check.

Para el frontend en Vercel: conectar el repo, root `frontend/`, y definir la
variable de entorno `VITE_API_URL` con la URL del backend. `frontend/vercel.json`
ya configura el SPA y los headers de cache.

## Variables de entorno

| Variable | Descripción | Obligatoria |
|----------|-------------|-------------|
| POSTGRES_USER | Usuario de PostgreSQL | Sí |
| POSTGRES_PASSWORD | Contraseña de PostgreSQL | Sí |
| POSTGRES_DB | Nombre de la base de datos | Sí |
| DATABASE_URL | Cadena de conexión completa a Postgres | Sí |
| SECRET_KEY | Clave para firmar los JWT (mín. 32 caracteres) | Sí |
| ANTHROPIC_API_KEY | Key de console.anthropic.com para el OCR | Sí |
| TIPO_CAMBIO_USD | Tipo de cambio RMB/USD por defecto | No (6.7) |
| UPLOAD_DIR | Carpeta de archivos subidos | No (./uploads) |
| CORS_ORIGINS | Orígenes permitidos, separados por coma | Sí |
| ACCESS_TOKEN_EXPIRE_HOURS | Horas de validez del token | No (8) |
| VITE_API_URL | URL del backend para el build del frontend | Sí (prod) |
| SMTP_HOST | Servidor SMTP para el correo de "olvidé mi contraseña" (ej. smtp.gmail.com) | No (vacío = el enlace queda en los logs) |
| SMTP_PORT | Puerto SMTP | No (587) |
| SMTP_USER | Cuenta que manda el correo | No |
| SMTP_PASSWORD | Contraseña de aplicación de esa cuenta (no la contraseña normal) | No |
| SMTP_FROM | Remitente del correo | No (usa SMTP_USER) |

## Usuarios del sistema

| Rol | Permisos |
|-----|----------|
| admin | Acceso total: usuarios, configuración, historial, cotizaciones y pedidos |
| vendedora | Crea cotizaciones, sube fotos (OCR), arma Packing List y genera pedidos; ve solo lo propio |
| contadora | Solo lectura del historial con totales financieros |

## Crear el primer usuario admin en producción

El script `seed.py` crea los usuarios iniciales (incluido el admin):

```bash
docker compose -f docker-compose.prod.yml exec backend python seed.py
```

Luego, desde el panel **Administración** se pueden crear el resto de los usuarios
y cambiar las contraseñas. Conviene cambiar la contraseña del admin tras el primer ingreso
(Administración → Editar → Cambiar contraseña).

## Actualizar el tipo de cambio RMB/USD

Desde la UI: ingresar como **admin** → **Administración** → sección
"Configuración del sistema" → escribir el nuevo valor → **Guardar**.

El nuevo tipo de cambio se aplica a las cotizaciones nuevas; cada sesión guarda
el tipo de cambio con el que fue creada.

## Estructura del proyecto

```
yuda/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # auth, ocr, packing, pedidos, admin
│   │   ├── core/            # config y seguridad
│   │   ├── models/          # modelos SQLAlchemy
│   │   ├── schemas/         # schemas Pydantic
│   │   ├── services/        # OCR, Excel, packing
│   │   └── main.py
│   ├── alembic/             # migraciones
│   ├── Dockerfile           # desarrollo
│   ├── Dockerfile.prod      # producción (multi-stage)
│   └── seed.py
├── frontend/
│   ├── src/                 # api, components, pages, store, types
│   ├── public/              # manifest.json e iconos PWA
│   ├── Dockerfile / Dockerfile.prod
│   ├── nginx.conf           # SPA + proxy en producción
│   └── vercel.json
├── docker-compose.yml       # desarrollo
├── docker-compose.prod.yml  # producción
├── deploy.sh
└── CHECKLIST_DEPLOY.md
```
