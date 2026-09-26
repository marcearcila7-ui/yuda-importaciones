import asyncio
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import exigir_acceso_sesion, require_roles
from app.api.routes.bodega import _ItemInspeccionado, _items_inspeccionados
from app.core.archivo_valida import detectar_tipo_documento, es_video_valido
from app.core.imagen_valida import detectar_tipo_imagen
from app.database import get_db
from app.models.cubicaje import TIPO_NOTA, TIPO_REPORTE, TIPO_RESPUESTA, CubicajeMensaje
from app.models.seguimiento import SeguimientoPedido
from app.models.sesion import Sesion
from app.models.user import User
from app.schemas.cubicaje import (
    AdjuntoCubicaje,
    CubicajeDetalle,
    CubicajeMensajeResponse,
    CubicajeNotaInput,
    CubicajeReporteInput,
    CubicajeRespuestaInput,
    CubicajeResumen,
    SobranteListaGenerada,
    SobranteListaItem,
    SobranteListaPreview,
)
from app.services.cubicaje_service import (
    LIMITE_MAX_CBM,
    LIMITE_MIN_CBM,
    RESULTADO_SOBRA,
    calcular_cbm_pedido,
    determinar_resultado,
)
from app.services.excel_service import generar_packing_list_excel
from app.services.notificacion_service import avisar_cubicaje_a_bodega, avisar_cubicaje_a_vendedora
from app.services.pdf_service import generar_packing_list_pdf
from app.services.storage_service import subir_documento, subir_excel, subir_foto, subir_pdf, subir_video

# Mismos tipos que "Adjuntos de esta etapa" en Seguimiento, más video: bodega y
# la vendedora pueden mandarse fotos y videos de evidencia, no solo documentos.
_ADJ_EXT = {
    ".pdf": ("pdf", "application/pdf"),
    ".jpg": ("imagen", "image/jpeg"),
    ".jpeg": ("imagen", "image/jpeg"),
    ".png": ("imagen", "image/png"),
    ".webp": ("imagen", "image/webp"),
    ".csv": ("csv", "text/csv"),
    ".xls": ("excel", "application/vnd.ms-excel"),
    ".xlsx": ("excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ".mp4": ("video", "video/mp4"),
    ".mov": ("video", "video/quicktime"),
    ".webm": ("video", "video/webm"),
}
_ADJ_CONTENT_TYPE = {
    "application/pdf": ("pdf", ".pdf"),
    "image/jpeg": ("imagen", ".jpg"),
    "image/png": ("imagen", ".png"),
    "image/webp": ("imagen", ".webp"),
    "text/csv": ("csv", ".csv"),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ("excel", ".xlsx"),
    "video/mp4": ("video", ".mp4"),
    "video/quicktime": ("video", ".mov"),
    "video/webm": ("video", ".webm"),
}
_ADJ_NO_SOPORTADO = (
    "Solo se permiten fotos (JPG, PNG, WEBP), videos (MP4, MOV, WEBM), PDF, CSV o Excel"
)
_ADJ_MAX_BYTES = 100 * 1024 * 1024

# Se monta en main.py bajo /api/v1
router = APIRouter(tags=["cubicaje"])


def _numero(sesion: Sesion) -> str:
    return f"YUDA-{sesion.fecha:%Y%m%d}-{sesion.id[:6].upper()}"


def _sesion_o_404(db: Session, sesion_id: str, usuario: User) -> Sesion:
    sesion = db.query(Sesion).filter(Sesion.id == sesion_id).first()
    if sesion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cotización no encontrada")
    exigir_acceso_sesion(db, sesion, usuario)
    return sesion


def _referencias_sobrante(db: Session, sesion_id: str) -> dict[str, int]:
    """Cuántas cajas quedaron sobrando por referencia, acumulado de todos los
    reportes "sobra" que bodega ha mandado para este pedido. Si reportó la
    misma referencia más de una vez (para corregirla), manda la más
    reciente -no se suman entre sí."""
    filas = (
        db.query(CubicajeMensaje)
        .filter(
            CubicajeMensaje.sesion_id == sesion_id,
            CubicajeMensaje.tipo == TIPO_REPORTE,
            CubicajeMensaje.resultado == RESULTADO_SOBRA,
            CubicajeMensaje.referencia.isnot(None),
        )
        .order_by(CubicajeMensaje.created_at.asc())
        .all()
    )
    mapa: dict[str, int] = {}
    for f in filas:
        if f.referencia and f.cajas_afectadas:
            mapa[f.referencia] = f.cajas_afectadas
    return mapa


class _ItemSobrante:
    """El mismo producto que bodega ya validó (fotos, descripción, precio,
    medidas), pero con "cajas" reemplazado por la cantidad que sobró -no la
    cantidad total confirmada. Es la única diferencia con el documento
    normal de la cotización corregida."""

    def __init__(self, base: object, cajas_sobrante: int) -> None:
        self._base = base
        self._cajas_sobrante = cajas_sobrante

    def __getattr__(self, nombre: str):
        if nombre == "ctns":
            return self._cajas_sobrante
        return getattr(self._base, nombre)


def _items_sobrante(db: Session, sesion: Sesion) -> list[_ItemSobrante]:
    mapa = _referencias_sobrante(db, sesion.id)
    if not mapa:
        return []
    # Sin las filas de "caja extra" (_ItemCajaExtra): la lista sobrante es un
    # número agregado por referencia, no un desglose de cajas irregulares.
    base_items = [i for i in _items_inspeccionados(db, sesion.id) if isinstance(i, _ItemInspeccionado)]
    return [_ItemSobrante(i, mapa[i.referencia]) for i in base_items if i.referencia in mapa]


@router.get("/sesiones/{sesion_id}/cubicaje/sobrante", response_model=SobranteListaPreview)
def obtener_sobrante_preview(
    sesion_id: str,
    usuario: User = Depends(require_roles("admin", "bodega")),
    db: Session = Depends(get_db),
) -> SobranteListaPreview:
    """Para que bodega confirme ANTES de generar el documento: qué
    referencias y cuántas cajas va a incluir la lista sobrante."""
    sesion = _sesion_o_404(db, sesion_id, usuario)
    items = _items_sobrante(db, sesion)
    return SobranteListaPreview(
        items=[
            SobranteListaItem(
                referencia=i.referencia or "",
                descripcion=i.descripcion_es or i.descripcion_en or "—",
                cajas=i._cajas_sobrante,
            )
            for i in items
        ]
    )


@router.post("/sesiones/{sesion_id}/cubicaje/sobrante/generar", response_model=SobranteListaGenerada)
def generar_lista_sobrante(
    sesion_id: str,
    usuario: User = Depends(require_roles("admin", "bodega")),
    db: Session = Depends(get_db),
) -> SobranteListaGenerada:
    """Genera el Excel y el PDF de la lista sobrante (mismo formato que la
    cotización corregida de bodega, filtrado a las referencias sobrantes con
    su cantidad real) y los sube al storage. No los manda todavía al chat:
    eso es una nota aparte con estos dos adjuntos, para reusar el mismo
    mecanismo de fotos/videos/archivos."""
    sesion = _sesion_o_404(db, sesion_id, usuario)
    items = _items_sobrante(db, sesion)
    if not items:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Todavía no se ha reportado ninguna referencia sobrante para este pedido"
        )

    excel_bytes = generar_packing_list_excel(items, sesion.nombre_cliente, sesion.tipo_cambio_usd, sesion.tipo_cotizacion)
    pdf_bytes = generar_packing_list_pdf(items, sesion.nombre_cliente, sesion.tipo_cambio_usd, sesion.tipo_cotizacion)

    fecha = datetime.now().strftime("%Y%m%d")
    base = f"cubicaje/{sesion_id}-sobrante-{uuid.uuid4().hex[:8]}"
    nombre_excel = f"{fecha}_{sesion.nombre_cliente}_ListaSobrante.xlsx"
    nombre_pdf = f"{fecha}_{sesion.nombre_cliente}_ListaSobrante.pdf"
    excel_url = subir_excel(excel_bytes, f"{base}.xlsx")
    pdf_url = subir_pdf(pdf_bytes, f"{base}.pdf")

    return SobranteListaGenerada(
        excel=AdjuntoCubicaje(url=excel_url, nombre=nombre_excel, tipo="excel"),
        pdf=AdjuntoCubicaje(url=pdf_url, nombre=nombre_pdf, tipo="pdf"),
    )


@router.post("/sesiones/{sesion_id}/cubicaje/adjunto", response_model=AdjuntoCubicaje)
async def subir_adjunto_cubicaje(
    sesion_id: str,
    archivo: UploadFile,
    usuario: User = Depends(require_roles("admin", "vendedora", "bodega")),
    db: Session = Depends(get_db),
) -> dict:
    """Sube una foto, video o documento para adjuntarlo a un mensaje del hilo
    de cubicaje (nota o respuesta). Devuelve {url, nombre, tipo}: el
    front arma el mensaje con eso, no se guarda nada acá todavía."""
    _sesion_o_404(db, sesion_id, usuario)

    nombre_original = archivo.filename or ""
    punto = nombre_original.rfind(".")
    extension = nombre_original[punto:].lower() if punto != -1 else ""

    if extension in _ADJ_EXT:
        tipo, content_type = _ADJ_EXT[extension]
    elif archivo.content_type in _ADJ_CONTENT_TYPE:
        tipo, extension = _ADJ_CONTENT_TYPE[archivo.content_type]
        content_type = archivo.content_type
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _ADJ_NO_SOPORTADO)

    contenido = await archivo.read()
    if len(contenido) > _ADJ_MAX_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El archivo no debe superar 100MB")

    # Valida el contenido REAL (magic bytes), no solo el content-type/extensión
    # declarados por el cliente (falsificables).
    if tipo == "imagen" and detectar_tipo_imagen(contenido) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _ADJ_NO_SOPORTADO)
    if tipo in ("pdf", "excel") and detectar_tipo_documento(contenido) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _ADJ_NO_SOPORTADO)
    if tipo == "video" and not es_video_valido(contenido):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _ADJ_NO_SOPORTADO)
    if tipo == "csv" and b"\x00" in contenido[:4096]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _ADJ_NO_SOPORTADO)

    nombre_archivo = f"cubicaje/{sesion_id}-{uuid.uuid4().hex[:8]}{extension}"
    loop = asyncio.get_event_loop()
    try:
        if tipo == "imagen":
            url = await loop.run_in_executor(None, lambda: subir_foto(contenido, nombre_archivo, content_type))
        elif tipo == "video":
            url = await loop.run_in_executor(None, lambda: subir_video(contenido, nombre_archivo, content_type))
        else:
            url = await loop.run_in_executor(None, lambda: subir_documento(contenido, nombre_archivo, content_type))
    except Exception as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "No se pudo guardar el archivo: el almacenamiento no está disponible. Intenta de nuevo en unos minutos.",
        ) from exc

    return {"url": url, "nombre": archivo.filename, "tipo": tipo}


def _resumen_texto(
    resultado: str, cbm: float, referencia: str | None, cajas: int | None, espacio: float | None,
    cbm_ajustado: float | None = None,
) -> str:
    cbm_texto = f"{cbm_ajustado} m³ (bodega ajustó; el sistema calculó {cbm})" if cbm_ajustado is not None else f"{cbm} m³ calculados"
    if resultado == RESULTADO_SOBRA and referencia and cajas:
        return f"sobraron {cajas} caja(s) de «{referencia}» ({cbm_texto})"
    if resultado == "falta" and espacio is not None:
        return f"faltan {espacio} m³ para completar el contenedor ({cbm_texto})"
    return f"cubicaje ajustado: {cbm_texto}"


def _mensaje_response(m: CubicajeMensaje, autores: dict[str, User]) -> CubicajeMensajeResponse:
    autor = autores.get(m.autor_id) if m.autor_id else None
    return CubicajeMensajeResponse(
        id=m.id,
        tipo=m.tipo,
        autor_id=m.autor_id,
        autor_nombre=autor.nombre if autor else (None if m.autor_id else "Cliente"),
        mensaje=m.mensaje,
        cbm_calculado=m.cbm_calculado,
        cbm_ajustado=m.cbm_ajustado,
        resultado=m.resultado,
        referencia=m.referencia,
        cajas_afectadas=m.cajas_afectadas,
        espacio_restante_cbm=m.espacio_restante_cbm,
        adjuntos=m.adjuntos,
        created_at=m.created_at,
    )


@router.get("/sesiones/{sesion_id}/cubicaje", response_model=CubicajeDetalle)
def obtener_cubicaje(
    sesion_id: str,
    usuario: User = Depends(require_roles("admin", "vendedora", "bodega")),
    db: Session = Depends(get_db),
) -> CubicajeDetalle:
    """El cálculo en vivo del cubicaje (con lo que bodega ya inspeccionó) más
    todo el hilo de reportes/notas/respuestas de este pedido. Se usa con
    polling rápido en ambas apps -por eso va todo en una sola llamada."""
    sesion = _sesion_o_404(db, sesion_id, usuario)

    cbm, referencias = calcular_cbm_pedido(db, sesion)
    resumen = CubicajeResumen(
        cbm_calculado=cbm,
        limite_min=LIMITE_MIN_CBM,
        limite_max=LIMITE_MAX_CBM,
        resultado=determinar_resultado(cbm),
        referencias=referencias,
    )

    filas = (
        db.query(CubicajeMensaje)
        .filter(CubicajeMensaje.sesion_id == sesion_id)
        .order_by(CubicajeMensaje.created_at.asc())
        .all()
    )
    autor_ids = {m.autor_id for m in filas}
    autores = {u.id: u for u in db.query(User).filter(User.id.in_(autor_ids)).all()} if autor_ids else {}

    # Quién está del otro lado de la conversación para cada app.
    seg = db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == sesion_id).first()
    vendedora = db.query(User).filter(User.id == sesion.user_id).first()
    asignado = (
        db.query(User).filter(User.id == seg.bodega_asignado_a_id).first()
        if seg and seg.bodega_asignado_a_id
        else None
    )

    return CubicajeDetalle(
        resumen=resumen,
        mensajes=[_mensaje_response(m, autores) for m in filas],
        vendedora_nombre=vendedora.nombre if vendedora else None,
        bodega_asignado_a_nombre=asignado.nombre if asignado else None,
    )


@router.post("/bodega/pedidos/{sesion_id}/cubicaje/reporte", response_model=CubicajeMensajeResponse)
def enviar_reporte_cubicaje(
    sesion_id: str,
    datos: CubicajeReporteInput,
    usuario: User = Depends(require_roles("admin", "bodega")),
    db: Session = Depends(get_db),
) -> CubicajeMensaje:
    """Bodega manda un reporte de cubicaje a la vendedora: el cálculo lo hace
    siempre el servidor (nunca se confía en un número mandado por el
    cliente), y bodega solo aporta la referencia/cajas que sobraron (si
    aplica) y una nota opcional."""
    sesion = _sesion_o_404(db, sesion_id, usuario)

    if datos.resultado not in ("sobra", "falta", "ajustado"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Resultado inválido")

    cbm, referencias = calcular_cbm_pedido(db, sesion)

    referencia = None
    cajas_afectadas = None
    espacio_restante = None
    if datos.resultado == "sobra":
        if not datos.referencia or datos.referencia not in referencias:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Selecciona una referencia real de este pedido"
            )
        if not datos.cajas_afectadas or datos.cajas_afectadas <= 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Indica cuántas cajas sobraron")
        referencia = datos.referencia
        cajas_afectadas = datos.cajas_afectadas
    elif datos.resultado == "falta":
        espacio_restante = round(LIMITE_MAX_CBM - cbm, 4)

    # cbm_ajustado es la corrección a mano de bodega: solo se guarda si de
    # verdad difiere del calculado (si mandan el mismo número, no aporta nada
    # aparte y solo confundiría mostrar "bodega ajustó a lo mismo").
    cbm_ajustado = (
        round(datos.cbm_ajustado, 4)
        if datos.cbm_ajustado is not None and round(datos.cbm_ajustado, 4) != cbm
        else None
    )

    mensaje = CubicajeMensaje(
        sesion_id=sesion_id,
        tipo=TIPO_REPORTE,
        autor_id=usuario.id,
        mensaje=(datos.nota or "").strip() or None,
        cbm_calculado=cbm,
        cbm_ajustado=cbm_ajustado,
        resultado=datos.resultado,
        referencia=referencia,
        cajas_afectadas=cajas_afectadas,
        espacio_restante_cbm=espacio_restante,
    )
    db.add(mensaje)

    seg = db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == sesion_id).first()
    resumen_texto = _resumen_texto(datos.resultado, cbm, referencia, cajas_afectadas, espacio_restante, cbm_ajustado)
    avisar_cubicaje_a_vendedora(db, sesion_id, _numero(sesion), sesion.nombre_cliente, sesion.user_id, resumen_texto)
    db.commit()
    db.refresh(mensaje)

    return _mensaje_response(mensaje, {usuario.id: usuario})


@router.post("/bodega/pedidos/{sesion_id}/cubicaje/nota", response_model=CubicajeMensajeResponse)
def agregar_nota_cubicaje(
    sesion_id: str,
    datos: CubicajeNotaInput,
    usuario: User = Depends(require_roles("admin", "bodega")),
    db: Session = Depends(get_db),
) -> CubicajeMensaje:
    """Nota libre de bodega en el hilo de cubicaje (no recalcula nada, es solo
    contexto adicional para la vendedora). Cualquiera de bodega puede
    agregarla, no solo quien tiene el pedido asignado."""
    sesion = _sesion_o_404(db, sesion_id, usuario)
    texto = datos.mensaje.strip()
    adjuntos = [a.model_dump() for a in datos.adjuntos] if datos.adjuntos else None
    if not texto and not adjuntos:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Escribe algo o adjunta un archivo para la nota")

    mensaje = CubicajeMensaje(
        sesion_id=sesion_id, tipo=TIPO_NOTA, autor_id=usuario.id, mensaje=texto or None, adjuntos=adjuntos,
    )
    db.add(mensaje)
    resumen_aviso = texto or "Envió un archivo adjunto"
    avisar_cubicaje_a_vendedora(db, sesion_id, _numero(sesion), sesion.nombre_cliente, sesion.user_id, resumen_aviso)
    db.commit()
    db.refresh(mensaje)

    return _mensaje_response(mensaje, {usuario.id: usuario})


@router.post("/sesiones/{sesion_id}/cubicaje/responder", response_model=CubicajeMensajeResponse)
def responder_cubicaje(
    sesion_id: str,
    datos: CubicajeRespuestaInput,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> CubicajeMensaje:
    """La vendedora (o Marcela) responde en el hilo de cubicaje. Avisa a
    quien tenga el pedido asignado en bodega (o a todo bodega/admin si nadie
    lo tiene asignado)."""
    sesion = _sesion_o_404(db, sesion_id, usuario)
    texto = datos.mensaje.strip()
    adjuntos = [a.model_dump() for a in datos.adjuntos] if datos.adjuntos else None
    if not texto and not adjuntos:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Escribe algo o adjunta un archivo para responder")

    mensaje = CubicajeMensaje(
        sesion_id=sesion_id, tipo=TIPO_RESPUESTA, autor_id=usuario.id, mensaje=texto or None, adjuntos=adjuntos,
    )
    db.add(mensaje)

    seg = db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == sesion_id).first()
    resumen_aviso = texto or "Envió un archivo adjunto"
    avisar_cubicaje_a_bodega(
        db, sesion_id, _numero(sesion), sesion.nombre_cliente,
        seg.bodega_asignado_a_id if seg else None, resumen_aviso,
    )
    db.commit()
    db.refresh(mensaje)

    return _mensaje_response(mensaje, {usuario.id: usuario})
