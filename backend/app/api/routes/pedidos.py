import io
import os
import re
import zipfile
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
from app.services.pdf_service import generar_pedido_pdf
from app.services.storage_service import subir_excel, subir_pdf

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


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
    fotos_bytes = descargar_imagenes_png(urls_fotos, lado_px=180)
    fotos_datauri = {url: bytes_a_data_uri(b) for url, b in fotos_bytes.items()}

    resultados: list[PedidoGeneradoInfo] = []

    # g. Un archivo por proveedor
    for clave, grupo in grupos.items():
        primero = grupo[0]
        contenido = generar_formato_pedido(
            primero.supplier_nombre, primero.supplier_numero, grupo, fecha_hoy,
            fotos=fotos_bytes,
        )
        contenido_pdf = generar_pedido_pdf(
            primero.supplier_nombre, primero.supplier_numero, grupo, fecha_hoy,
            fotos=fotos_datauri,
        )

        nombre_archivo = f"{fecha_str}_{_sanitizar(clave)}_Pedido.xlsx"
        nombre_pdf = f"{fecha_str}_{_sanitizar(clave)}_Pedido.pdf"
        ruta_en_bucket = f"{sesion_id}/{nombre_archivo}"
        ruta_pdf = f"{sesion_id}/{nombre_pdf}"

        # Subir Excel y PDF a Supabase Storage (carpeta por sesión)
        url_descarga = subir_excel(contenido, ruta_en_bucket)
        url_pdf = subir_pdf(contenido_pdf, ruta_pdf)

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
