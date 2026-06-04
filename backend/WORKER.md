# Worker de la cola de OCR

El OCR de los lotes puede correr en un **proceso aparte** del web, para que el
web quede siempre responsivo y el procesamiento **sobreviva reinicios**.

La cola vive en Postgres (tablas `lotes_ocr` / `lote_items`); no hace falta Redis.

## Cómo funciona

- Con `USE_WORKER=false` (default): el OCR corre en segundo plano dentro del web
  (comportamiento histórico). No hace falta worker.
- Con `USE_WORKER=true`: al tocar "procesar", el web solo **encola** el lote
  (`estado = encolado`). El **worker** lo toma, lo marca `procesando`, corre el
  OCR y lo deja `completado`.

El tope global de concurrencia de OCR y los reintentos viven en `ocr_service`,
así que aplican en el worker igual que antes.

## Desplegar el worker en Railway

1. **Deploy del código** (este commit). Como `USE_WORKER` viene en `false`, nada
   cambia todavía: el sistema sigue funcionando como hasta ahora.
2. En el proyecto de Railway, **crear un servicio nuevo** desde el mismo repo
   (carpeta `backend`, mismo Dockerfile).
3. En ese servicio, fijar el **Start Command**:
   ```
   python -m app.worker
   ```
4. Darle al worker las **mismas variables** que el web: `DATABASE_URL`
   (el mismo Postgres), `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`,
   `SECRET_KEY`. (No necesita puerto ni dominio.)
5. Cuando el worker esté corriendo, poner **`USE_WORKER=true`** en el **servicio
   web** (y opcionalmente en el worker). A partir de ahí el web encola y el worker
   procesa.

Para volver atrás: poner `USE_WORKER=false` en el web (vuelve a procesar en
segundo plano) y apagar el worker.

## Escalar

Se pueden correr varias réplicas del worker: el reclamo de lotes usa
`FOR UPDATE SKIP LOCKED`, así que no se pisan al tomar trabajo. Nota: la
recuperación de huérfanos al arrancar (`procesando` → `encolado`) asume **un solo
worker**; para varios habría que agregar un heartbeat por lote.
