# Runbook de deploy — YUDA Importaciones (Railway)

Arquitectura: 3 servicios en Railway (**PostgreSQL** + **backend** FastAPI + **frontend** nginx) + **Supabase** externo (almacenamiento de fotos).

El repo ya trae `backend/railway.json` y `frontend/railway.json` que fijan `Dockerfile.prod`. Solo hay que fijar el **Root Directory** de cada servicio.

## 1. Claves (rotar/generar antes)
- [ ] Supabase **service_role** key (Settings → API) — va solo en el backend, nunca en el frontend
- [ ] **ANTHROPIC_API_KEY** (console.anthropic.com)
- [ ] **SECRET_KEY** ≥ 32 chars aleatorios: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`

## 2. Proyecto y base de datos
- [ ] `railway login` y crear/seleccionar el proyecto
- [ ] Agregar **PostgreSQL** (provee `DATABASE_URL`)

## 3. Servicio backend
- [ ] Root Directory = `backend`
- [ ] Variables:
  ```
  DATABASE_URL=${{Postgres.DATABASE_URL}}
  SECRET_KEY=<generada>
  ANTHROPIC_API_KEY=<rotada>
  SUPABASE_URL=https://<proyecto>.supabase.co
  SUPABASE_SERVICE_KEY=<rotada>
  TIPO_CAMBIO_USD=6.7
  UPLOAD_DIR=/app/uploads
  ACCESS_TOKEN_EXPIRE_HOURS=8
  CORS_ORIGINS=<URL del frontend, se completa en el paso 5>
  SEED_ADMIN_PASSWORD=<elegir>
  SEED_VENDEDORA_PASSWORD=<elegir>
  SEED_CONTADORA_PASSWORD=<elegir>
  ```
- [ ] Generar dominio público → **URL del backend**
- [ ] En el contenedor: `alembic upgrade head` (crea las tablas 0001→0007)
- [ ] En el contenedor: `python seed.py` (crea los usuarios con las contraseñas de las variables SEED_*)

## 4. Servicio frontend
- [ ] Root Directory = `frontend`
- [ ] Variable `VITE_API_URL=<URL del backend>` (Vite la congela en el build → el backend debe existir antes)
- [ ] Generar dominio público → **URL del frontend**

## 5. Cerrar el círculo y verificar
- [ ] Backend → `CORS_ORIGINS` = URL exacta del frontend (sin `/` final) → redeploy
- [ ] `curl https://<backend>/` → `{"status":"ok","sistema":"YUDA Importaciones"}`
- [ ] Login desde el navegador con un usuario del seed
- [ ] Una vendedora sube una foto y el OCR responde

## 6. Correo de "olvidé mi contraseña" (agregado después del alta inicial)
- [ ] En Gmail (`soporteyuda26@gmail.com` o la cuenta que se use): activar verificación en 2 pasos si no la tiene
- [ ] Generar una **contraseña de aplicación**: Cuenta de Google → Seguridad → Verificación en 2 pasos → Contraseñas de aplicaciones
- [ ] Backend → agregar `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_USER=<esa cuenta>`, `SMTP_PASSWORD=<la contraseña de aplicación>` → redeploy
- [ ] Sin esto configurado, el flujo funciona igual pero el enlace de recuperación solo queda en los logs del backend, no sale el correo de verdad

## Notas
- El backend **no arranca** si falta `SECRET_KEY` o `DATABASE_URL` (falla explícito, a propósito).
- `USE_WORKER=false` (default): el OCR corre en el backend web, un solo servicio. Para separarlo, crear un servicio worker con start command `python -m app.worker` y `USE_WORKER=true` en el backend.
- Las fotos van a Supabase (bucket público `fotos`/`pedidos`), no al disco → no hace falta volumen.
- Si el frontend sirve un bundle viejo tras deploy: recarga forzada (Cmd+Shift+R).
