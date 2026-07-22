import io
import logging
import multiprocessing
import os
import re
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import exigir_roles, get_current_user
from app.database import get_db
from app.models.item import Item
from app.models.pedido import PedidoGenerado
from app.models.sesion import Sesion
from app.models.user import User
from app.schemas.pedidos import (
    GenerarPedidosResponse,
    PedidoGeneradoInfo,
    PedidoGeneradoResponse,
)
from app.services.excel_service import agrupar_items_por_supplier, generar_formato_pedido
from app.services.imagen_service import bytes_a_data_uri, descargar_imagenes_png
from app.services.pdf_service import html_pedido, render_pdf
from app.services.storage_service import subir_excel, subir_pdf
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
    """Devuelve la sesión o lanza 404. Una vendedora solo puede acceder a las
    suyas (403 en caso contrario); admin y contadora ven todas."""
    sesion = db.query(Sesion).filter(Sesion.id == sesion_id).first()
    if sesion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesión no encontrada",
        )
    if usuario.rol.value == "vendedora" and sesion.user_id != usuario.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sin permisos sobre esta cotización",
        )
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
    # 600 px de lado: la foto va grande en el Excel y en el PDF (es LA referencia
    # de lo que se pidió), así que se baja al doble del tamaño en que se muestra
    # para que no se vea pixelada ni en pantalla ni impresa.
    fotos_bytes = descargar_imagenes_png(urls_fotos, lado_px=600)
    fotos_datauri = {url: bytes_a_data_uri(b) for url, b in fotos_bytes.items()}

    resultados: list[PedidoGeneradoInfo] = []

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
            fotos=fotos_bytes,
        )
        htmls.append(
            html_pedido(
                primero.supplier_nombre, primero.supplier_numero, grupo, fecha_hoy,
                fotos=fotos_datauri,
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

    # Subir Excel y PDF a Supabase Storage (carpeta por sesión). Las subidas son
    # espera de red, así que van todas a la vez en hilos.
    def _subir(clave: str) -> tuple[str, str]:
        ruta = f"{sesion_id}/{fecha_str}_{_sanitizar(clave)}_Pedido"
        return (
            subir_excel(excels[clave], f"{ruta}.xlsx"),
            subir_pdf(pdfs[clave], f"{ruta}.pdf"),
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
        url_descarga, url_pdf = urls[clave]

        # Upsert del registro en pedidos_generados
        registro = (
            db.query(PedidoGenerado)
            .filter(
                PedidoGenerado.sesion_id == sesion_id,
                PedidoGenerado.supplier == clave,
            )
            .first()
        )
        if registro:
            registro.archivo_xlsx_url = url_descarga
            registro.archivo_pdf_url = url_pdf
            registro.fecha_generacion = datetime.now()
        else:
            registro = PedidoGenerado(
                sesion_id=sesion_id,
                supplier=clave,
                archivo_xlsx_url=url_descarga,
                archivo_pdf_url=url_pdf,
            )
            db.add(registro)

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
