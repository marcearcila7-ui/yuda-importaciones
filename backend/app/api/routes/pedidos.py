import io
import logging
import multiprocessing
import os
import re
import time
import uuid
import zipfile
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import exigir_acceso_sesion, exigir_roles, get_current_user
from app.database import get_db
from app.models.cliente import Cliente
from app.models.cliente_vendedora import ClienteVendedora
from app.models.pedido_bodega_actividad import PedidoBodegaActividad
from app.models.item import Item
from app.models.pedido import PedidoGenerado, PedidoGeneradoItem
from app.models.seguimiento import ESTADOS_ENVIO, ESTADOS_VENDEDORA, SeguimientoPedido
from app.models.sesion import Sesion
from app.models.user import RolUsuario, User
from app.schemas.bodega import ActividadBodegaResponse, PedidoBodegaSeguimientoResumen
from app.schemas.pedidos import (
    EnviarABodegaInput,
    FechaTentativaInput,
    GenerarPedidosResponse,
    PedidoGeneradoInfo,
    PedidoGeneradoResponse,
)
from app.schemas.inspeccion import InspeccionSesionResponse
from app.services.aviso_cliente_service import avisar_cliente_fecha_tentativa, formatear_fecha_legible
from app.services.excel_service import (
    agrupar_items_por_supplier,
    generar_csv_pedido,
    generar_formato_pedido,
)
from app.services.actividad_bodega_service import registrar_actividad_bodega
from app.services.imagen_service import bytes_a_data_uri, descargar_imagenes
from app.services.inspeccion_service import construir_inspeccion_sesion
from app.services.notificacion_service import avisar_pedido_regenerado_tras_revision
from app.services.pdf_service import html_pedido, render_pdf
from app.services.storage_service import subir_csv, subir_excel, subir_pdf
from app.services.traduccion_service import descripcion_zh_util, traducir_descripciones_zh

router = APIRouter(prefix="/pedidos", tags=["pedidos"])

logger = logging.getLogger(__name__)

# Cada PDF del formato de pedido tarda varios segundos (WeasyPrint tiene que
# incrustar la fuente china, que trae decenas de miles de glifos). Con muchos
# proveedores eso se vuelve minutos, así que los PDFs se renderizan en varios
# procesos a la vez. "spawn" evita los bloqueos de hacer fork desde un hilo del
# servidor; los procesos solo reciben el HTML (texto) y devuelven los bytes.
_MAX_PROCESOS_PDF = 8


def _obtener_sesion(db: Session, sesion_id: str, usuario: User) -> Sesion:
    """Devuelve la sesión o lanza 404/403 (ver `exigir_acceso_sesion`: dueña,
    o vendedora colaboradora del cliente vinculado; admin y contadora ven todas)."""
    sesion = db.query(Sesion).filter(Sesion.id == sesion_id).first()
    if sesion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesión no encontrada",
        )
    exigir_acceso_sesion(db, sesion, usuario)
    return sesion


def _sanitizar(texto: str) -> str:
    """Reemplaza espacios y caracteres especiales por guión bajo para el nombre de archivo"""
    return re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_")


class _ItemCajasCliente:
    """Envuelve un ítem usando las cajas que pidió el cliente (cantidad_solicitada)
    en lugar de las CTNS internas, sin tocar el valor en la base de datos. Los
    generadores de Excel/PDF leen `.ctns`, así que solo reemplazamos ese campo y
    delegamos todo lo demás al ítem original."""

    def __init__(self, item: Item, ctns: int) -> None:
        self._item = item
        self.ctns = ctns

    def __getattr__(self, nombre: str):  # solo se invoca para atributos no propios
        return getattr(self._item, nombre)


@router.post("/{sesion_id}/generar", response_model=GenerarPedidosResponse)
def generar_pedidos(
    sesion_id: str,
    usar_cantidades_cliente: bool = False,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GenerarPedidosResponse:
    """Genera un Excel de Formato Pedido por cada proveedor de la sesión.

    Si `usar_cantidades_cliente` es true, usa las cajas que pidió el cliente
    desde su portal (cantidad_solicitada) en lugar de las CTNS internas.
    """
    exigir_roles(usuario, "admin", "vendedora")

    # a. La sesión debe existir
    sesion = _obtener_sesion(db, sesion_id, usuario)

    # a.1. Una vez el contenedor ya está en bodega o más adelante, regenerar un
    # pedido borraría en silencio la revisión que bodega ya hizo (o peor, la
    # de un pedido que ya viajó). De "proveedor_recibio" para atrás sigue
    # siendo seguro: es el ajuste de último momento antes de que bodega lo vea.
    seguimiento = db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == sesion_id).first()
    if seguimiento is not None and ESTADOS_ENVIO.index(seguimiento.estado) >= ESTADOS_ENVIO.index("en_bodega"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Esta cotización ya está en bodega o más adelante: no se puede regenerar el "
                "pedido a proveedor desde acá. Si algo cambió, coordina con bodega o Marcela."
            ),
        )

    # a.2. Sin marca de embarque (iniciales del cliente) el proveedor no tiene
    # cómo separar estas cajas de las de otro pedido en su bodega. Se exige acá
    # (no solo en la pantalla) para que no se pueda generar sin ella por ningún
    # camino.
    if not (sesion.shipping_mark or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Escribe la marca de embarque (iniciales del cliente) antes de generar el pedido",
        )

    # b. Ítems ordenados por orden
    items = (
        db.query(Item)
        .filter(Item.sesion_id == sesion_id)
        .order_by(Item.orden.asc())
        .all()
    )

    # c. Debe haber ítems
    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La sesión no tiene ítems",
        )

    warnings: list[str] = []

    if usar_cantidades_cliente:
        # Basta con que el cliente haya ENVIADO las cantidades desde el portal; ya
        # no se exige una segunda confirmación (se genera directo con lo enviado).
        if sesion.pedido_recibido_at is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El cliente aún no ha enviado las cantidades desde el portal",
            )
        # d/e. Usar las cajas que pidió el cliente; avisar de las que dejó en 0
        items_validos = []
        for item in items:
            cajas = item.cantidad_solicitada or 0
            if cajas <= 0:
                nombre = item.descripcion_es or item.item_no or "sin código"
                warnings.append(
                    f"El cliente no pidió cajas de «{nombre}»; no se incluye en el pedido"
                )
                continue
            items_validos.append(_ItemCajasCliente(item, cajas))
    else:
        # d. Advertencias por ítems con CTNS=0
        for item in items:
            if not item.ctns or item.ctns == 0:
                codigo = item.item_no or "sin código"
                proveedor = item.supplier_nombre or "Sin proveedor"
                warnings.append(
                    f"Ítem {codigo} del proveedor {proveedor} tiene CTNS=0 y no se incluirá en el pedido"
                )
        # e. Solo ítems con CTNS > 0
        items_validos = [item for item in items if item.ctns and item.ctns > 0]

    # f.0. El formato del proveedor lleva la descripción en español Y en chino. El
    # OCR muchas veces deja en el campo chino lo que decía el cartel de la tienda
    # (razón social, dirección), así que lo que no sirva se traduce ahora y queda
    # guardado con el producto: se traduce una sola vez, no en cada generación.
    sin_zh = [i for i in items_validos if not descripcion_zh_util(i)]
    if sin_zh:
        # Los ítems pueden venir envueltos (cantidades del cliente): se escribe
        # sobre el ítem real de la base, no sobre la envoltura.
        reales = {i.id: i for i in items}
        traducciones = traducir_descripciones_zh(sin_zh)
        for item_id, zh in traducciones.items():
            if item_id in reales:
                reales[item_id].descripcion_zh = zh
        if traducciones:
            db.commit()

    # f. Agrupar por proveedor
    grupos = agrupar_items_por_supplier(items_validos)

    fecha_hoy = datetime.now().date()
    fecha_str = fecha_hoy.strftime("%Y%m%d")

    # f.2. Descargar TODAS las fotos una sola vez y en paralelo (antes se bajaban
    # dos veces —Excel y PDF— y de forma secuencial, lo que hacía muy lenta y a
    # veces colgaba la generación). Se reutilizan como bytes (Excel) y data URI (PDF).
    urls_fotos = [
        (getattr(i, "foto_final_url", None) or getattr(i, "foto_url", None))
        for i in items_validos
    ]
    # 900 px de lado: la foto va grande en el Excel y en el PDF (es LA referencia
    # de lo que se pidió), así que se baja al triple del tamaño en que se muestra
    # (300 px) para que se vea nítida también impresa, no solo en pantalla.
    fotos_bytes = descargar_imagenes(urls_fotos, lado_px=900)
    fotos_datauri = {url: bytes_a_data_uri(b) for url, b in fotos_bytes.items()}

    resultados: list[PedidoGeneradoInfo] = []
    regenerados_tras_revision: list[str] = []

    # g. Un archivo por proveedor. El Excel y el HTML se arman al momento (son
    # instantáneos); los PDFs, que son lo lento, se renderizan en paralelo.
    claves = list(grupos)
    t0 = time.perf_counter()
    excels: dict[str, bytes] = {}
    htmls: list[str] = []
    for clave in claves:
        grupo = grupos[clave]
        primero = grupo[0]
        excels[clave] = generar_formato_pedido(
            primero.supplier_nombre, primero.supplier_numero, grupo, fecha_hoy,
            fotos=fotos_bytes, shipping_mark=sesion.shipping_mark,
        )
        htmls.append(
            html_pedido(
                primero.supplier_nombre, primero.supplier_numero, grupo, fecha_hoy,
                fotos=fotos_datauri, shipping_mark=sesion.shipping_mark,
            )
        )

    pdfs: dict[str, bytes] = {}
    if len(claves) > 1:
        try:
            with ProcessPoolExecutor(
                max_workers=min(len(claves), _MAX_PROCESOS_PDF),
                mp_context=multiprocessing.get_context("spawn"),
            ) as pool:
                pdfs = dict(zip(claves, pool.map(render_pdf, htmls)))
        except Exception:  # si el entorno no deja crear procesos, se hace en fila
            logger.exception("No se pudo renderizar en paralelo; se hace secuencial")
            pdfs = {}
    if not pdfs:
        pdfs = {clave: render_pdf(html) for clave, html in zip(claves, htmls)}
    t_pdfs = time.perf_counter() - t0

    # CSV: liviano, se genera al vuelo (no como Excel/PDF que sí valen la pena
    # paralelizar). Es fundamental que todo pedido tenga esta versión también.
    csvs: dict[str, bytes] = {
        clave: generar_csv_pedido(grupos[clave][0].supplier_nombre, grupos[clave][0].supplier_numero, grupos[clave], fecha_hoy)
        for clave in claves
    }

    # Subir Excel, PDF y CSV a Supabase Storage (carpeta por sesión). Las
    # subidas son espera de red, así que van todas a la vez en hilos.
    def _subir(clave: str) -> tuple[str, str, str]:
        ruta = f"{sesion_id}/{fecha_str}_{_sanitizar(clave)}_Pedido"
        return (
            subir_excel(excels[clave], f"{ruta}.xlsx"),
            subir_pdf(pdfs[clave], f"{ruta}.pdf"),
            subir_csv(csvs[clave], f"{ruta}.csv"),
        )

    t1 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=min(len(claves), 8)) as hilos:
        urls = dict(zip(claves, hilos.map(_subir, claves)))
    logger.info(
        "generar_pedidos sesion=%s proveedores=%s pdfs=%.1fs subidas=%.1fs",
        sesion_id, len(claves), t_pdfs, time.perf_counter() - t1,
    )

    for clave in claves:
        grupo = grupos[clave]
        nombre_archivo = f"{fecha_str}_{_sanitizar(clave)}_Pedido.xlsx"
        url_descarga, url_pdf, url_csv = urls[clave]

        # Upsert del registro en pedidos_generados. Si ya existía (la vendedora
        # regeneró porque el cliente cambió algo), se toma como el nuevo pedido
        # base: se limpia cualquier revisión de bodega anterior, porque ya no
        # correspondería a lo que se está pidiendo ahora.
        registro = (
            db.query(PedidoGenerado)
            .filter(
                PedidoGenerado.sesion_id == sesion_id,
                PedidoGenerado.supplier == clave,
            )
            .first()
        )
        if registro:
            if registro.revisado_en_bodega_at is not None:
                # Bodega ya había contado este proveedor y esa revisión se va
                # a perder: que alguien se entere, no que se descubra después.
                regenerados_tras_revision.append(clave)
            registro.archivo_xlsx_url = url_descarga
            registro.archivo_pdf_url = url_pdf
            registro.archivo_csv_url = url_csv
            registro.archivo_real_xlsx_url = None
            registro.archivo_real_pdf_url = None
            registro.archivo_real_csv_url = None
            registro.revisado_en_bodega_at = None
            registro.fecha_generacion = datetime.now()
            db.query(PedidoGeneradoItem).filter(
                PedidoGeneradoItem.pedido_generado_id == registro.id
            ).delete()
        else:
            registro = PedidoGenerado(
                sesion_id=sesion_id,
                supplier=clave,
                archivo_xlsx_url=url_descarga,
                archivo_pdf_url=url_pdf,
                archivo_csv_url=url_csv,
            )
            db.add(registro)
            db.flush()  # asigna registro.id para las líneas de abajo

        for item in grupo:
            db.add(
                PedidoGeneradoItem(
                    pedido_generado_id=registro.id,
                    item_id=item.id,
                    cantidad_pedida=item.ctns,
                )
            )

        resultados.append(
            PedidoGeneradoInfo(
                supplier=clave,
                archivo_nombre=nombre_archivo,
                url_descarga=url_descarga,
                url_pdf=url_pdf,
                items_count=len(grupo),
            )
        )

    db.commit()

    if regenerados_tras_revision:
        numero = f"YUDA-{sesion.fecha:%Y%m%d}-{sesion.id[:6].upper()}"
        for clave in regenerados_tras_revision:
            avisar_pedido_regenerado_tras_revision(
                db, sesion_id, numero, sesion.nombre_cliente, sesion.user_id, clave
            )
        db.commit()

    # h. Respuesta
    return GenerarPedidosResponse(pedidos=resultados, warnings=warnings)


@router.get("/{sesion_id}", response_model=list[PedidoGeneradoResponse])
def listar_pedidos(
    sesion_id: str,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PedidoGenerado]:
    """Lista los pedidos generados de la sesión (más recientes primero)"""
    _obtener_sesion(db, sesion_id, usuario)
    return (
        db.query(PedidoGenerado)
        .filter(PedidoGenerado.sesion_id == sesion_id)
        .order_by(PedidoGenerado.fecha_generacion.desc())
        .all()
    )


@router.patch("/{pedido_generado_id}/fecha-tentativa", response_model=PedidoGeneradoResponse)
def actualizar_fecha_tentativa(
    pedido_generado_id: str,
    datos: FechaTentativaInput,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PedidoGenerado:
    """La vendedora carga o corrige la fecha aproximada que dio ESTE
    proveedor (no toda la cotización: cada proveedor tiene la suya). Si
    cambió de verdad, se le avisa al cliente por correo y WhatsApp,
    mencionando a qué proveedor corresponde."""
    exigir_roles(usuario, "admin", "vendedora")
    pedido = db.query(PedidoGenerado).filter(PedidoGenerado.id == pedido_generado_id).first()
    if pedido is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
    sesion = db.query(Sesion).filter(Sesion.id == pedido.sesion_id).first()
    if sesion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cotización no encontrada")
    exigir_acceso_sesion(db, sesion, usuario)

    cambio = pedido.fecha_tentativa_entrega != datos.fecha
    pedido.fecha_tentativa_entrega = datos.fecha
    db.commit()
    db.refresh(pedido)

    if cambio and sesion.cliente_id:
        cliente = db.query(Cliente).filter(Cliente.id == sesion.cliente_id).first()
        if cliente is not None:
            numero = f"YUDA-{sesion.fecha:%Y%m%d}-{sesion.id[:6].upper()}"
            avisar_cliente_fecha_tentativa(
                cliente, sesion.id, numero, formatear_fecha_legible(datos.fecha.isoformat()), pedido.supplier
            )

    return pedido


@router.get("/{sesion_id}/descargar-zip")
def descargar_zip(
    sesion_id: str,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Empaqueta todos los xlsx de la sesión en un ZIP en memoria"""
    sesion = _obtener_sesion(db, sesion_id, usuario)

    pedidos = (
        db.query(PedidoGenerado)
        .filter(PedidoGenerado.sesion_id == sesion_id)
        .all()
    )
    if not pedidos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay pedidos generados para esta sesión",
        )

    # ZIP en memoria (no se guarda en disco). Los archivos se bajan desde Supabase.
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for pedido in pedidos:
            # Excel del proveedor
            nombre = os.path.basename(pedido.archivo_xlsx_url)
            zf.writestr(nombre, httpx.get(pedido.archivo_xlsx_url).content)
            # PDF del proveedor (si existe)
            if pedido.archivo_pdf_url:
                nombre_pdf = os.path.basename(pedido.archivo_pdf_url)
                zf.writestr(nombre_pdf, httpx.get(pedido.archivo_pdf_url).content)

    fecha_str = datetime.now().strftime("%Y%m%d")
    nombre_zip = f"{fecha_str}_{sesion.nombre_cliente}_Pedidos.zip"

    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nombre_zip}"'},
    )


@router.get("/{sesion_id}/cotizacion-inspeccion", response_model=InspeccionSesionResponse)
def obtener_cotizacion_inspeccion(
    sesion_id: str,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InspeccionSesionResponse:
    """Vista de solo lectura para la vendedora: la cotización con las
    correcciones que bodega guardó al inspeccionar (cantidades reales,
    medidas, fotos/video de evidencia). Nunca es lo que ve el cliente."""
    sesion = _obtener_sesion(db, sesion_id, usuario)
    return construir_inspeccion_sesion(db, sesion)


_TIPOS_ARCHIVO_PEDIDO = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ("archivo_xlsx_url", subir_excel),
    "application/pdf": ("archivo_pdf_url", subir_pdf),
    "text/csv": ("archivo_csv_url", subir_csv),
}


@router.post("/generados/{pedido_generado_id}/reemplazar-archivo", response_model=PedidoGeneradoResponse)
async def reemplazar_archivo_pedido_generado(
    pedido_generado_id: str,
    archivo: UploadFile,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PedidoGenerado:
    """Si el Excel/PDF/CSV que generó el sistema para un proveedor necesita un
    ajuste a mano, la vendedora sube acá la versión corregida y reemplaza la
    que bodega va a ver. No cambia nada de los datos internos del pedido, solo
    el archivo."""
    pedido = db.query(PedidoGenerado).filter(PedidoGenerado.id == pedido_generado_id).first()
    if pedido is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
    _obtener_sesion(db, pedido.sesion_id, usuario)

    info = _TIPOS_ARCHIVO_PEDIDO.get(archivo.content_type or "")
    if info is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Solo se permiten archivos Excel (.xlsx), PDF o CSV"
        )
    campo_url, subir = info

    contenido = await archivo.read()
    if len(contenido) > 25 * 1024 * 1024:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El archivo no debe superar 25MB")

    nombre_archivo = f"pedidos/{pedido.id}/manual_{uuid.uuid4().hex}_{archivo.filename or 'archivo'}"
    url = subir(contenido, nombre_archivo)
    setattr(pedido, campo_url, url)

    registrar_actividad_bodega(
        db, pedido.sesion_id, usuario.id, "archivo_reemplazado",
        f"Reemplazó el archivo de la orden a «{pedido.supplier}»",
    )
    db.commit()
    db.refresh(pedido)
    return pedido


@router.post("/{sesion_id}/enviar-a-bodega")
def enviar_a_bodega(
    sesion_id: str,
    datos: EnviarABodegaInput,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Botón guiado: envía el pedido a bodega (junto con la cotización del
    cliente y las órdenes a proveedor ya generadas) y, si se eligió, lo asigna
    directo a alguien de bodega en el mismo paso."""
    exigir_roles(usuario, "admin", "vendedora")
    sesion = _obtener_sesion(db, sesion_id, usuario)

    if db.query(PedidoGenerado).filter(PedidoGenerado.sesion_id == sesion_id).count() == 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Genera los pedidos a proveedor antes de enviar a bodega"
        )

    seg = db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == sesion_id).first()
    if seg is not None and seg.estado not in ESTADOS_VENDEDORA:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Esta cotización ya está en bodega o más adelante"
        )

    asignado = None
    if datos.asignado_a_id:
        asignado = (
            db.query(User)
            .filter(User.id == datos.asignado_a_id, User.rol.in_([RolUsuario.admin, RolUsuario.bodega]), User.activo)
            .first()
        )
        if asignado is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ese usuario no es válido para asignarle un pedido")

    # Reusa la lógica ya existente de cambio de estado (notificaciones al
    # cliente, avisos internos, bitácora) en vez de duplicarla acá.
    from app.api.routes.clientes import actualizar_seguimiento as _actualizar_seguimiento
    from app.schemas.seguimiento import SeguimientoResponse, SeguimientoUpdate

    resultado = _actualizar_seguimiento(
        sesion_id,
        SeguimientoUpdate(estado="proveedor_recibio", novedades=seg.novedades if seg else None),
        usuario,
        db,
    )

    if asignado is not None:
        resultado.bodega_asignado_a_id = asignado.id
        resultado.bodega_asignado_en = datetime.now(timezone.utc)
        resultado.bodega_asignado_por_id = usuario.id
        registrar_actividad_bodega(
            db, sesion_id, usuario.id, "asignado", f"Asignado a {asignado.nombre} al enviar a bodega"
        )
        db.commit()
        db.refresh(resultado)

    return SeguimientoResponse.model_validate(resultado).model_dump()


@router.get("/bodega-resumen", response_model=list[PedidoBodegaSeguimientoResumen])
def bodega_resumen(
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PedidoBodegaSeguimientoResumen]:
    """Panel de control para la vendedora: todo lo que se ha enviado a
    bodega, sin importar el cliente. Qué le devolvió bodega, quién lo tiene
    asignado y quién actualizó qué. Admin ve todas; la vendedora solo las
    suyas (dueña o colaboradora)."""
    exigir_roles(usuario, "admin", "vendedora")

    query = (
        db.query(Sesion, SeguimientoPedido)
        .join(SeguimientoPedido, SeguimientoPedido.sesion_id == Sesion.id)
        .filter(SeguimientoPedido.estado.in_(ESTADOS_ENVIO[ESTADOS_ENVIO.index("proveedor_recibio"):]))
    )
    if usuario.rol.value == "vendedora":
        compartidos = db.query(ClienteVendedora.cliente_id).filter(
            ClienteVendedora.vendedora_id == usuario.id
        )
        clientes_con_acceso = db.query(Cliente.id).filter(
            (Cliente.vendedora_id == usuario.id) | (Cliente.id.in_(compartidos))
        )
        query = query.filter(
            (Sesion.user_id == usuario.id) | (Sesion.cliente_id.in_(clientes_con_acceso))
        )

    filas = query.order_by(SeguimientoPedido.updated_at.desc()).all()
    if not filas:
        return []

    sesion_ids = [s.id for s, _ in filas]
    asignado_ids = {seg.bodega_asignado_a_id for _, seg in filas if seg.bodega_asignado_a_id}
    asignados_por_id = (
        {u.id: u for u in db.query(User).filter(User.id.in_(asignado_ids)).all()} if asignado_ids else {}
    )

    ordenes_por_sesion: dict[str, list[PedidoGenerado]] = {}
    for pg in db.query(PedidoGenerado).filter(PedidoGenerado.sesion_id.in_(sesion_ids)).all():
        ordenes_por_sesion.setdefault(pg.sesion_id, []).append(pg)

    actividad_por_sesion: dict[str, list[ActividadBodegaResponse]] = {}
    actividad_filas = (
        db.query(PedidoBodegaActividad, User)
        .outerjoin(User, User.id == PedidoBodegaActividad.usuario_id)
        .filter(PedidoBodegaActividad.sesion_id.in_(sesion_ids))
        .order_by(PedidoBodegaActividad.created_at.desc())
        .all()
    )
    for a, u in actividad_filas:
        lista = actividad_por_sesion.setdefault(a.sesion_id, [])
        if len(lista) < 5:
            lista.append(
                ActividadBodegaResponse(
                    usuario_nombre=u.nombre if u else None, tipo=a.tipo, detalle=a.detalle, created_at=a.created_at
                )
            )

    resultado: list[PedidoBodegaSeguimientoResumen] = []
    for sesion, seg in filas:
        ordenes = ordenes_por_sesion.get(sesion.id, [])
        asignado = asignados_por_id.get(seg.bodega_asignado_a_id) if seg.bodega_asignado_a_id else None
        resultado.append(
            PedidoBodegaSeguimientoResumen(
                sesion_id=sesion.id,
                numero=f"YUDA-{sesion.fecha:%Y%m%d}-{sesion.id[:6].upper()}",
                cliente_nombre=sesion.nombre_cliente,
                fecha=sesion.fecha,
                estado_envio=seg.estado,
                total_ordenes=len(ordenes),
                ordenes_revisadas=sum(1 for o in ordenes if o.revisado_en_bodega_at is not None),
                bodega_asignado_a_id=seg.bodega_asignado_a_id,
                bodega_asignado_a_nombre=asignado.nombre if asignado else None,
                actividad_reciente=actividad_por_sesion.get(sesion.id, []),
            )
        )
    return resultado
