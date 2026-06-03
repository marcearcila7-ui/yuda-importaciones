import io
import os
import re
import zipfile
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
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
from app.services.storage_service import subir_excel

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


def _exigir_roles(usuario: User, *roles: str) -> None:
    """Lanza 403 si el rol del usuario no está entre los permitidos"""
    if usuario.rol.value not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sin permisos para esta acción",
        )


def _obtener_sesion(db: Session, sesion_id: str) -> Sesion:
    """Devuelve la sesión o lanza 404"""
    sesion = db.query(Sesion).filter(Sesion.id == sesion_id).first()
    if sesion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesión no encontrada",
        )
    return sesion


def _sanitizar(texto: str) -> str:
    """Reemplaza espacios y caracteres especiales por guión bajo para el nombre de archivo"""
    return re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_")


@router.post("/{sesion_id}/generar", response_model=GenerarPedidosResponse)
def generar_pedidos(
    sesion_id: str,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GenerarPedidosResponse:
    """Genera un Excel de Formato Pedido por cada proveedor de la sesión"""
    _exigir_roles(usuario, "admin", "vendedora")

    # a. La sesión debe existir
    _obtener_sesion(db, sesion_id)

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

    # d. Advertencias por ítems con CTNS=0
    warnings: list[str] = []
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

    resultados: list[PedidoGeneradoInfo] = []

    # g. Un archivo por proveedor
    for clave, grupo in grupos.items():
        primero = grupo[0]
        contenido = generar_formato_pedido(
            primero.supplier_nombre, primero.supplier_numero, grupo, fecha_hoy
        )

        nombre_archivo = f"{fecha_str}_{_sanitizar(clave)}_Pedido.xlsx"
        ruta_en_bucket = f"{sesion_id}/{nombre_archivo}"

        # Subir el Excel a Supabase Storage (carpeta por sesión) y usar su URL pública
        url_descarga = subir_excel(contenido, ruta_en_bucket)

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
            registro.fecha_generacion = datetime.now()
        else:
            registro = PedidoGenerado(
                sesion_id=sesion_id,
                supplier=clave,
                archivo_xlsx_url=url_descarga,
            )
            db.add(registro)

        resultados.append(
            PedidoGeneradoInfo(
                supplier=clave,
                archivo_nombre=nombre_archivo,
                url_descarga=url_descarga,
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
    _obtener_sesion(db, sesion_id)
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
    sesion = _obtener_sesion(db, sesion_id)

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
            nombre = os.path.basename(pedido.archivo_xlsx_url)
            response = httpx.get(pedido.archivo_xlsx_url)
            zf.writestr(nombre, response.content)

    fecha_str = datetime.now().strftime("%Y%m%d")
    nombre_zip = f"{fecha_str}_{sesion.nombre_cliente}_Pedidos.zip"

    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nombre_zip}"'},
    )
