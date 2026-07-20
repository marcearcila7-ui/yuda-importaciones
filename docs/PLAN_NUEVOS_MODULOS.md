# YUDA — Plan de implementación: Nuevos módulos

Fuente: `YUDA_Requisitos_Nuevos_Modulos.docx` + formatos Excel de Marcela
(`FOTMATO COTIZACION.xls`, `FORMATO PEDIDO.xls`, `FORMATO FACTURA.xls`, `FOTMATO CUENTA.xlsx`).
Elaborado: 2026-07-19.

## Decisiones cerradas (con Sara)
1. **Alcance:** los 4 módulos, en orden **M1 → M2 → M3 → M4**.
2. **Tasa de cambio RMB→USD:** TRM **manual por contenedor** (no global).
3. **"Logística 5%" = "Comisión YUDA":** mismo concepto (5% que YUDA cobra al cliente).
   Etiqueta en la plataforma: **"Comisión YUDA"**.
4. **Alerta pago 70% a tiendas:** notificación **in-app** (reusar sistema de campana existente).

## Bloqueante pendiente
- **Falta el formato Excel de clientes externos del consolidado (Tipo B)** para el Módulo 3.
  Es el único de los 5 pendientes del doc que no llegó. No bloquea M1/M2/M4; sí bloquea la
  importación de M3. Pedir a Marcela antes de arrancar la Fase 3.

---

## Estado del código (lo que ya existe y se reutiliza)

- **Backend:** FastAPI + SQLAlchemy + Alembic. Última migración: `0012_token_version`.
- **Rol `contadora` ya existe** (`models/user.py::RolUsuario`). Hoy ve Historial + detalle de
  cotización (solo lectura). Guard en frontend: `ProtectedRoute roles={[...]}` (`App.tsx`).
- **`Sesion`** (cotización) ya tiene `tipo_cambio_usd`, `user_id` (empleada que la creó),
  `cliente_id`. → base para FX y para el ranking de empleadas.
- **`Item`** ya tiene `largo_cm/ancho_cm/alto_cm/cbm/price_rmb/ctns/qty_por_ctn`. → editar
  medidas "en plataforma" (Opción A del doc) es directo, sin importar Excel.
- **`SeguimientoPedido`** con `hitos`, `estado`, `monto_venta`, tracking/BL. → cubre Tipo A del
  consolidado; falta Tipo B.
- **`Cliente`** con login propio + **portal** (`/portal`, `PortalProtectedRoute`). → base para la
  vista del cliente de M2 y M3.
- **`Configuracion`** (key-value). **`Notificacion`** (campana). **Servicios** `excel_service`,
  `pdf_service`, `storage_service`, templates en `app/templates/`.

---

## FASE 1 — Facturación (M1)

**Objetivo:** desde una cotización confirmada, actualizar medidas reales de cajas y generar la
factura en USD lista para el cliente.

**Medidas de cajas (Opción A — edición en plataforma):**
- UI para editar por ítem/caja: `largo_cm`, `ancho_cm`, `alto_cm`, `peso (kg)`, `cantidad de cajas`.
- `cbm` auto = Largo×Ancho×Alto × cant. (el doc dice "L×A×A", es typo; se usa L×W×H — ya así en código).
- Falta agregar **peso real por caja** si no está a nivel editable (hay `gw` en Item; confirmar semántica).
- Export/Import Excel = **opción B, secundaria**. Se implementa solo si Marcela lo pide; con Opción A no es necesario.

**Factura en USD (`FORMATO FACTURA.xls`):** columnas del formato real →
`ITEM No | DESCRIPTION | CTN | QTY | TOTAL QTY | UNIT (USD) | AMOUNT` + `TOTAL USD`.
Respecto al packing list se **eliminan**: foto, precio RMB, CBM, material/uso, chino/inglés.
Se **conservan**: descripción, cantidad, USD, total, vendedora.
- Botón **"Generar Factura"** → PDF (reusar `pdf_service`) y/o Excel (reusar `excel_service`).
- USD por ítem = `price_rmb / trm_del_contenedor` (ver Fase 4 / entidad Contenedor).
- Incluir encabezado e datos bancarios del formato (Y&H IMPORT & EXPORT, banco, SWIFT, etc.).

**Entregables backend:** endpoints `PATCH` medidas por ítem; `POST /facturas/{sesion_id}/generar`.
**Migración:** `0013` — campos de peso/medidas faltantes en `Item` si aplica; tabla `facturas`
(id, sesion_id, numero, fecha, archivo_pdf_url, archivo_xlsx_url, total_usd).

---

## FASE 2 — Cuentas de clientes (M2)

**Formato real (`FOTMATO CUENTA.xlsx`)** — es un **libro por cliente/contenedor**, no un resumen:
Encabezado: `CLIENTE | NIT | CONTENEDOR | FECHA | AÑO`.
Filas (ledger): `ENVIO | FECHA | GUIA | DESCRIPCION | VALOR MERCANCIA | COMISIÓN YUDA (5%) | ABONO | SALDO | NOTA`.

**Modelos nuevos (migración `0014`):**
- `CuentaCliente` (opcional; o derivar por cliente): agregados calculados.
- `MovimientoCuenta`: `cliente_id`, `contenedor_id`, `fecha`, `guia`, `descripcion`,
  `valor_mercancia`, `comision_yuda` (auto = valor × 5%, % configurable), `abono`, `saldo` (auto
  acumulado), `nota`. Tipos: valores en USD.
- Agregados del estado de cuenta (doc 2.1): compras totales, abonos, comisión, **saldo pendiente
  auto**, fecha último abono, observaciones.

**Vista del cliente (doc 2.2):** en el **portal existente** (login que ya tiene el cliente),
solo lectura, solo su cuenta. Descarga PDF opcional (reusar `pdf_service`).
> Nota: el doc pregunta login vs enlace vs correo. El portal ya usa **login**, así que se reutiliza
> eso salvo que Marcela pida enlace único.

---

## FASE 3 — Consolidado / Tracking (M3)

**Tipo A (cliente completo):** ya cubierto por `SeguimientoPedido`. Solo integrar/rotular.

**Tipo B (cliente externo)** — NUEVO. 4 etapas en orden (doc 3.2):
1. Entrega de mercancía a bodega — fecha
2. Llegada a bodega Yiwu — fecha
3. Salida de bodega — fecha
4. Llegada a Colombia — fecha
Todas registradas por el operativo YUDA. Cliente ve estado en solo lectura.

**Modelos nuevos (migración `0015`):** `ClienteExterno` (o reusar `Cliente` con flag `tipo`),
`EnvioExterno` (mercancía + 4 fechas de etapa + estado). **Import Excel** del formato de clientes
externos → **BLOQUEADO hasta recibir el formato**.

---

## FASE 4 — Módulo Contadora (M4)

Es el panel paraguas de la contadora; integra M1–M3 + cotizaciones existentes.

### 4.0 Entidad Contenedor / Embarque (transversal, habilita TRM manual)
Nueva entidad `Contenedor`: `id`, `nombre/codigo`, `trm_usd` (TRM manual), `fecha`, estado.
Agrupa sesiones/envíos y provee la tasa para facturas (F1) y cuentas (F2).
`Sesion.tipo_cambio_usd` queda como fallback; la TRM del contenedor manda cuando existe.

### 4.1 Pagos a tiendas 30/70 (migración `0016`)
Formato de referencia: `FORMATO PEDIDO.xls` (orden a tienda, depósito/saldo).
Modelo `PedidoTienda`: `nombre_tienda`, `fecha_pedido`, `monto_total` (CNY),
`monto_30` (auto), `fecha_pago_30`, `fecha_estimada_entrega` (auto ~20 días), `fecha_real_entrega`,
`monto_70` (auto), `fecha_pago_70`, `pct_comision_tienda` (0/1/3%…), `monto_comision` (auto = total×%),
`estado` (Pendiente/Parcial/Pagado), `empleada_id`.
- **Alerta in-app**: cuando se acerca la fecha del saldo 70% → `Notificacion` a la contadora
  (reusar `notificacion_service`; worker/cron ya hay `worker.py`).

### 4.2 Comisiones de tiendas → YUDA
Vista/consulta derivada de `PedidoTienda` (`monto_comision`, `fecha_recibo`, `pedido_asociado`).
Filtro y totalización por período (mes/trimestre/año). Tiendas sin comisión = 0%.

### 4.3 Ranking de empleadas
Agregación por `Sesion.user_id` (empleada) cruzando ventas (`monto_venta`) y comisiones generadas.
Ranking por período + gráfico/tabla comparativa.

### 4.4 Panel consolidado de la contadora
Una vista `/contadora` (rol `contadora` + `admin`) con:
- Cotizaciones activas/cerradas (ya existe — integrar).
- Cuentas de clientes: saldos por cobrar (M2).
- Pagos pendientes a tiendas: saldos 70% por pagar (4.1) + alertas.
- Comisiones recibidas por período (4.2).
- Ranking/comisiones por empleada (4.3).
- **Exportar todo a Excel/PDF** (reusar servicios).

---

## Secuencia de migraciones Alembic (desde 0012)
- `0013` Facturación (Item medidas/peso + tabla `facturas`)
- `0014` Cuentas de clientes (`movimientos_cuenta`)
- `0015` Consolidado Tipo B (`clientes_externos`, `envios_externos`)
- `0016` Módulo Contadora (`contenedores`, `pedidos_tienda`)

## Permisos / navegación
- Nueva ruta `/contadora` → `ProtectedRoute roles={['contadora','admin']}`.
- Cuentas y facturas: `admin`, `contadora` (+ vendedora solo lectura de lo suyo, a confirmar).
- Portal cliente (M2/M3): rol cliente, solo lo suyo, solo lectura.
- Textos UI en **español neutro**; nav ya soporta ES/EN/中文 (mantener claves i18n).

## Riesgos / a confirmar con Marcela
- Formato Excel Tipo B (bloquea import de M3).
- Semántica exacta de `peso` por caja vs `gw` existente en `Item`.
- ¿La comisión de la tienda a YUDA es en CNY y se reporta aparte de la comisión YUDA al cliente (5%)? (son dos comisiones distintas: tienda→YUDA y YUDA→cliente).
