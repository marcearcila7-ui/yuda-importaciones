import asyncio
import re
import secrets
import string
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import (
    exigir_acceso_sesion,
    require_roles,
    vendedora_tiene_acceso_cliente,
)
from app.core.config import settings
from app.database import get_db
from app.services.borrado_service import (
    borrar_sesiones,
    limpiar_storage,
    tiene_movimientos_cliente,
)
from app.models.cliente import ORIGEN_IMPORTADO_CONTABLE, Cliente
from app.models.cliente_vendedora import ClienteActividad, ClienteVendedora
from app.models.cuenta import MovimientoCuenta, calcular_comision, convertir_abono
from app.services.estado_cuenta_service import (
    generar_estado_cuenta_excel,
    generar_estado_cuenta_pdf,
)
from app.models.seguimiento import (
    CAMPOS_SOLO_ADMIN,
    ESTADO_DISPARA_AVISO,
    ESTADO_INICIAL,
    ESTADOS_ENVIO,
    ESTADOS_VENDEDORA,
    SeguimientoPedido,
)
from app.models.item import Item
from app.models.pedido import PedidoGenerado
from app.models.sesion import PEDIDO_POR_CONFIRMAR, Sesion
from app.models.user import RolUsuario, User
from app.data.contable_clientes import CONTABLE_CLIENTES
from app.schemas.cliente import (
    ActividadInput,
    ActividadResponse,
    AsignarVendedorasInput,
    ClienteColaboracionResponse,
    ClienteResponse,
    ClienteUpdate,
    ContableClientePreview,
    CotizacionResumenCliente,
    ImportarContableInput,
    ImportarContableUnoInput,
    SincronizarClienteContableInput,
    ImportarContableResultado,
    ResetPasswordRequest,
    VendedoraAsignadaResponse,
    VendedoraBasica,
)
from app.schemas.cuenta import (
    EstadoCuentaResponse,
    MovimientoCreate,
    MovimientoUpdate,
)
from app.schemas.packing import EnviarAConfirmarInput, SesionResponse
from app.schemas.seguimiento import SeguimientoResponse, SeguimientoUpdate
from app.services.actividad_bodega_service import registrar_actividad_bodega
from app.services.cuenta_service import construir_estado_cuenta
from app.services.notificacion_service import (
    avisar_envio_a_vendedora,
    avisar_listo_para_envio,
)
from app.services.aviso_cliente_service import (
    avisar_cliente_aprobar_despacho,
    avisar_cliente_despachado,
    avisar_cliente_en_destino,
    avisar_cliente_entregado,
    avisar_cliente_pedido_en_proveedor,
)
from app.services.storage_service import borrar_archivos, ruta_desde_url, subir_documento, subir_foto, subir_pdf
from app.services.yuda_contable_service import (
    buscar_clientes_contable,
    listar_todos_clientes_contable,
    obtener_pdf_estado_cuenta_contable,
)
from app.core.security import hash_password

# Se monta en main.py bajo /api/v1 (sin prefijo propio)
router = APIRouter(tags=["clientes"])


# Clave de plantilla para la importación masiva de Yuda Contable: no se puede
# mandar una clave distinta a cada cliente uno por uno, así que todos entran
# con la misma y el portal los OBLIGA a cambiarla en su primer ingreso
# (Cliente.debe_cambiar_password / POST /portal/cambiar-password).
PASSWORD_PLANTILLA_CONTABLE = "Yuda2026**"


def _slug_email(nombre: str, dominio: str, ocupados: set[str]) -> str:
    """Usuario de portal a partir del nombre: 'Juan Pérez' -> 'juanperez@dominio'.
    Si ya existe (mismo nombre repetido, o choca con otro cliente), le agrega
    un número al final hasta encontrar uno libre."""
    sin_acentos = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^a-z0-9]", "", sin_acentos.lower()) or "cliente"
    email = f"{base}@{dominio}"
    contador = 2
    while email in ocupados:
        email = f"{base}{contador}@{dominio}"
        contador += 1
    ocupados.add(email)
    return email


def _cliente_response(
    cliente: Cliente, usuario: User, roles_por_usuario: dict[str, str] | None = None
) -> ClienteResponse:
    """Convierte el cliente a su forma pública, ocultando la sigla de Yuda
    Contable si quien pregunta no es admin/contadora: es un dato interno de
    Marcela para conciliar cuentas, no algo que una vendedora necesite ver."""
    resp = ClienteResponse.model_validate(cliente)
    if usuario.rol.value not in ("admin", "contadora"):
        resp.sigla = None
    rol_dueno = (roles_por_usuario or {}).get(cliente.vendedora_id)
    resp.pendiente_asignacion = cliente.origen == ORIGEN_IMPORTADO_CONTABLE and rol_dueno == "admin"
    return resp


def _roles_por_usuario(db: Session, clientes: list[Cliente]) -> dict[str, str]:
    """{vendedora_id: rol} de todos los dueños de esta tanda de clientes, para
    calcular pendiente_asignacion sin una consulta por cliente."""
    dueno_ids = {c.vendedora_id for c in clientes}
    if not dueno_ids:
        return {}
    return {u.id: u.rol.value for u in db.query(User).filter(User.id.in_(dueno_ids)).all()}


def _cliente_autorizado(db: Session, cliente_id: str, usuario: User) -> Cliente:
    """Devuelve el cliente si el usuario puede gestionarlo; si no, 404/403"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if cliente is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    if (
        usuario.rol.value == "vendedora"
        and cliente.vendedora_id != usuario.id
        and not vendedora_tiene_acceso_cliente(db, cliente_id, usuario.id)
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin permisos sobre este cliente")
    return cliente


def _exigir_dueno_o_admin(cliente: Cliente, usuario: User) -> None:
    """Para acciones destructivas o sensibles (borrar cliente, resetear su
    contraseña del portal): el acceso compartido de la Fase 1 (ClienteVendedora)
    solo da colaboración/visibilidad, no estas acciones. Debe ser admin o la
    vendedora dueña real."""
    if usuario.rol.value == "vendedora" and cliente.vendedora_id != usuario.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo la vendedora dueña de este cliente puede hacer esto",
        )


def _sesion_autorizada(db: Session, sesion_id: str, usuario: User) -> Sesion:
    """Devuelve la sesión si el usuario puede gestionarla; si no, 404/403."""
    sesion = db.query(Sesion).filter(Sesion.id == sesion_id).first()
    if sesion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cotización no encontrada")
    exigir_acceso_sesion(db, sesion, usuario)
    return sesion


# ──────────────── CLIENTES (CRUD) ────────────────
# Ya no existe un POST /clientes de creación manual a propósito: todo cliente
# tiene que nacer en Yuda Contable (app aparte) y llegar acá por
# sincronización automática (POST /clientes/sincronizar-desde-contable) o
# importación manual (POST /clientes/importar-contable-uno /
# /clientes/importar-contable). Los clientes con origen "manual" que ya
# existían de antes de esta regla se conservan tal cual (ver ORIGEN_MANUAL).


@router.get("/clientes", response_model=list[ClienteResponse])
def listar_clientes(
    usuario: User = Depends(require_roles("admin", "vendedora", "contadora")),
    db: Session = Depends(get_db),
) -> list[ClienteResponse]:
    """Lista clientes: la vendedora ve los suyos y los que Marcela le comparta;
    admin y contadora ven todos."""
    query = db.query(Cliente)
    if usuario.rol.value == "vendedora":
        compartidos = db.query(ClienteVendedora.cliente_id).filter(
            ClienteVendedora.vendedora_id == usuario.id
        )
        query = query.filter(
            (Cliente.vendedora_id == usuario.id) | (Cliente.id.in_(compartidos))
        )
    clientes = query.order_by(Cliente.created_at.desc()).all()
    roles = _roles_por_usuario(db, clientes)
    return [_cliente_response(c, usuario, roles) for c in clientes]


@router.get("/clientes/buscar-contable", response_model=list[ContableClientePreview])
def buscar_contable(
    q: str = Query(..., min_length=2),
    usuario: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> list[ContableClientePreview]:
    """Busca clientes de Yuda Contable EN VIVO, por su API interna (no la
    lista fija que usa /importar-contable/preview). 502 si no se pudo
    conectar (no configurada, o esa app no respondió). Va ANTES de
    /clientes/{cliente_id} a propósito: si no, esa ruta paramétrica capturaba
    "buscar-contable" como si fuera un cliente_id y esto siempre daba 404
    (mismo bug que tuvo /pedidos/bodega-resumen)."""
    resultados = buscar_clientes_contable(q)
    if resultados is None:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "No se pudo conectar con Yuda Contable")
    existentes = {c.sigla: c.id for c in db.query(Cliente).filter(Cliente.sigla.isnot(None)).all()}
    return [
        ContableClientePreview(
            sigla=r["sigla"],
            nombre=r.get("nombre_completo"),
            pais=r.get("pais"),
            telefono=r.get("telefono"),
            ya_existe=r["sigla"] in existentes,
            cliente_id_existente=existentes.get(r["sigla"]),
        )
        for r in resultados
    ]


@router.get("/clientes/no-sincronizados", response_model=list[ContableClientePreview])
def clientes_no_sincronizados(
    usuario: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> list[ContableClientePreview]:
    """Todos los clientes que existen en Yuda Contable pero todavía NO en el
    cotizador (ni importados ni sincronizados automáticamente al crearlos
    allá) -para el selector "nombre + sigla" de la pantalla de Clientes.
    502 si no se pudo conectar con Yuda Contable."""
    todos = listar_todos_clientes_contable()
    if todos is None:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "No se pudo conectar con Yuda Contable")
    existentes = {sigla for (sigla,) in db.query(Cliente.sigla).filter(Cliente.sigla.isnot(None)).all()}
    return [
        ContableClientePreview(
            sigla=r["sigla"],
            nombre=r.get("nombre_completo"),
            pais=r.get("pais"),
            telefono=r.get("telefono"),
            ya_existe=False,
            cliente_id_existente=None,
        )
        for r in todos
        if r["sigla"] not in existentes
    ]


@router.get("/clientes/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente(
    cliente_id: str,
    # La contadora ve la ficha del cliente en solo lectura (para conciliar).
    usuario: User = Depends(require_roles("admin", "vendedora", "contadora")),
    db: Session = Depends(get_db),
) -> ClienteResponse:
    cliente = _cliente_autorizado(db, cliente_id, usuario)
    return _cliente_response(cliente, usuario, _roles_por_usuario(db, [cliente]))


@router.get("/clientes/{cliente_id}/cotizaciones", response_model=list[SesionResponse])
def cotizaciones_del_cliente(
    cliente_id: str,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> list[SesionResponse]:
    """Cotizaciones vinculadas a un cliente, con la etapa real de envío de
    cada una (para que la vendedora las pueda clasificar sin adivinar)."""
    _cliente_autorizado(db, cliente_id, usuario)
    sesiones = (
        db.query(Sesion)
        .filter(Sesion.cliente_id == cliente_id)
        .order_by(Sesion.created_at.desc())
        .all()
    )
    sesion_ids = [s.id for s in sesiones]
    estados = (
        {
            seg.sesion_id: seg.estado
            for seg in db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id.in_(sesion_ids)).all()
        }
        if sesion_ids
        else {}
    )
    return [
        SesionResponse.model_validate(s).model_copy(update={"estado_envio": estados.get(s.id)})
        for s in sesiones
    ]


@router.patch("/clientes/{cliente_id}", response_model=ClienteResponse)
def actualizar_cliente(
    cliente_id: str,
    datos: ClienteUpdate,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> ClienteResponse:
    cliente = _cliente_autorizado(db, cliente_id, usuario)
    cambios = datos.model_dump(exclude_unset=True)
    if "vendedora_id" in cambios and usuario.rol.value != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Marcela puede reasignar la vendedora dueña")
    if cambios.get("vendedora_id"):
        nueva = db.query(User).filter(User.id == cambios["vendedora_id"], User.rol == RolUsuario.vendedora).first()
        if nueva is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Esa vendedora no existe")
    if "sigla" in cambios and usuario.rol.value != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo Marcela puede editar la sigla de Yuda Contable")
    if cambios.get("sigla"):
        sigla = cambios["sigla"].strip().upper()
        cambios["sigla"] = sigla
        repetida = (
            db.query(Cliente)
            .filter(Cliente.sigla == sigla, Cliente.id != cliente_id)
            .first()
        )
        if repetida is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"La sigla {sigla} ya está asignada a {repetida.nombre}"
            )
    for campo, valor in cambios.items():
        setattr(cliente, campo, valor)
    db.commit()
    db.refresh(cliente)
    return _cliente_response(cliente, usuario, _roles_por_usuario(db, [cliente]))


# ──────────────── Colaboración: clientes compartidos entre vendedoras ────────────────


@router.get("/clientes/{cliente_id}/colaboracion", response_model=ClienteColaboracionResponse)
def obtener_colaboracion_cliente(
    cliente_id: str,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> ClienteColaboracionResponse:
    """Vista consolidada del cliente: quién lo gestiona (dueña + asignadas),
    todas sus cotizaciones (de cualquier vendedora que le haya cotizado) y la
    bitácora de actividad. Es lo que usa Marcela para ver el trabajo de cada
    vendedora sobre un cliente compartido y armar la factura final."""
    cliente = _cliente_autorizado(db, cliente_id, usuario)

    duena = db.query(User).filter(User.id == cliente.vendedora_id).first()

    asignaciones = (
        db.query(ClienteVendedora, User)
        .join(User, User.id == ClienteVendedora.vendedora_id)
        .filter(ClienteVendedora.cliente_id == cliente_id)
        .order_by(ClienteVendedora.created_at.asc())
        .all()
    )
    ids_asignadores = {a.asignado_por_id for a, _ in asignaciones if a.asignado_por_id}
    asignadores = {
        u.id: u.nombre for u in db.query(User).filter(User.id.in_(ids_asignadores)).all()
    } if ids_asignadores else {}
    asignadas = [
        VendedoraAsignadaResponse(
            vendedora=VendedoraBasica.model_validate(u),
            asignado_por=asignadores.get(asignacion.asignado_por_id) if asignacion.asignado_por_id else None,
            created_at=asignacion.created_at,
        )
        for asignacion, u in asignaciones
    ]

    sesiones = (
        db.query(Sesion, User)
        .join(User, User.id == Sesion.user_id)
        .filter(Sesion.cliente_id == cliente_id)
        .order_by(Sesion.created_at.desc())
        .all()
    )
    seguimientos = {
        s.sesion_id: s.estado
        for s in db.query(SeguimientoPedido).filter(
            SeguimientoPedido.sesion_id.in_([s.id for s, _ in sesiones])
        )
    }
    cotizaciones = [
        CotizacionResumenCliente(
            sesion_id=sesion.id,
            numero=f"YUDA-{sesion.fecha:%Y%m%d}-{sesion.id[:6].upper()}",
            fecha=sesion.created_at,
            vendedora_nombre=vend.nombre,
            pedido_estado=sesion.pedido_estado,
            estado_envio=seguimientos.get(sesion.id),
        )
        for sesion, vend in sesiones
    ]

    actividad_filas = (
        db.query(ClienteActividad, User)
        .join(User, User.id == ClienteActividad.usuario_id)
        .filter(ClienteActividad.cliente_id == cliente_id)
        .order_by(ClienteActividad.created_at.desc())
        .all()
    )
    actividad = [
        ActividadResponse(
            id=a.id,
            usuario_id=a.usuario_id,
            usuario_nombre=autor.nombre,
            nota=a.nota,
            created_at=a.created_at,
        )
        for a, autor in actividad_filas
    ]

    return ClienteColaboracionResponse(
        duena=VendedoraBasica.model_validate(duena),
        asignadas=asignadas,
        cotizaciones=cotizaciones,
        actividad=actividad,
    )


@router.post(
    "/clientes/{cliente_id}/actividad",
    response_model=ActividadResponse,
    status_code=status.HTTP_201_CREATED,
)
def agregar_actividad_cliente(
    cliente_id: str,
    datos: ActividadInput,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> ActividadResponse:
    """Deja una nota libre sobre el cliente (llamada, acuerdo, novedad). Queda
    firmada con el autor para que, si el cliente es compartido, se vea quién
    hizo qué."""
    _cliente_autorizado(db, cliente_id, usuario)
    nota = datos.nota.strip()
    if not nota:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Escribe algo en la nota")
    actividad = ClienteActividad(cliente_id=cliente_id, usuario_id=usuario.id, nota=nota)
    db.add(actividad)
    db.commit()
    db.refresh(actividad)
    return ActividadResponse(
        id=actividad.id,
        usuario_id=usuario.id,
        usuario_nombre=usuario.nombre,
        nota=actividad.nota,
        created_at=actividad.created_at,
    )


@router.post(
    "/clientes/{cliente_id}/vendedoras",
    response_model=list[VendedoraAsignadaResponse],
    status_code=status.HTTP_201_CREATED,
)
def asignar_vendedoras_cliente(
    cliente_id: str,
    datos: AsignarVendedorasInput,
    usuario: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> list[VendedoraAsignadaResponse]:
    """Marcela comparte este cliente con una o más vendedoras adicionales
    (además de la dueña). No duplica si ya estaba asignada."""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if cliente is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")

    ya_asignadas = {
        vid
        for (vid,) in db.query(ClienteVendedora.vendedora_id).filter(
            ClienteVendedora.cliente_id == cliente_id
        )
    }
    for vendedora_id in datos.vendedora_ids:
        if vendedora_id == cliente.vendedora_id or vendedora_id in ya_asignadas:
            continue
        vendedora = db.query(User).filter(User.id == vendedora_id, User.rol == RolUsuario.vendedora).first()
        if vendedora is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"La vendedora {vendedora_id} no existe")
        db.add(ClienteVendedora(cliente_id=cliente_id, vendedora_id=vendedora_id, asignado_por_id=usuario.id))
    db.commit()

    asignaciones = (
        db.query(ClienteVendedora, User)
        .join(User, User.id == ClienteVendedora.vendedora_id)
        .filter(ClienteVendedora.cliente_id == cliente_id)
        .order_by(ClienteVendedora.created_at.asc())
        .all()
    )
    return [
        VendedoraAsignadaResponse(
            vendedora=VendedoraBasica.model_validate(u),
            asignado_por=usuario.nombre if a.asignado_por_id == usuario.id else None,
            created_at=a.created_at,
        )
        for a, u in asignaciones
    ]


@router.delete("/clientes/{cliente_id}/vendedoras/{vendedora_id}", status_code=status.HTTP_204_NO_CONTENT)
def quitar_vendedora_cliente(
    cliente_id: str,
    vendedora_id: str,
    usuario: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> None:
    """Marcela le quita a una vendedora el acceso compartido a este cliente
    (la dueña original no se puede quitar por acá: eso es reasignar, con
    PATCH /clientes/{id} y el campo vendedora_id)."""
    asignacion = (
        db.query(ClienteVendedora)
        .filter(ClienteVendedora.cliente_id == cliente_id, ClienteVendedora.vendedora_id == vendedora_id)
        .first()
    )
    if asignacion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esa vendedora no está asignada a este cliente")
    db.delete(asignacion)
    db.commit()


@router.get("/clientes/importar-contable/preview", response_model=list[ContableClientePreview])
def preview_importar_contable(
    usuario: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> list[ContableClientePreview]:
    """Compara la foto fija de clientes de Yuda Contable contra lo que ya
    existe acá (por sigla), para que Marcela decida cuáles traer. No trae
    nada financiero, solo nombre/sigla/país/teléfono."""
    existentes = {
        c.sigla: c.id for c in db.query(Cliente).filter(Cliente.sigla.isnot(None)).all()
    }
    return [
        ContableClientePreview(
            sigla=c["sigla"],
            nombre=c["nombre"],
            pais=c["pais"],
            telefono=c["telefono"],
            ya_existe=c["sigla"] in existentes,
            cliente_id_existente=existentes.get(c["sigla"]),
        )
        for c in CONTABLE_CLIENTES
    ]


def _crear_cliente_desde_contable(
    db: Session, usuario: User, sigla: str, nombre: str | None, telefono: str | None, pais: str | None
) -> Cliente:
    """Crea el Cliente con la clave de plantilla forzada, igual en la
    importación en bloque (lista fija) que en la importación individual
    (búsqueda en vivo) -mismo criterio en ambas."""
    emails_ocupados = {e for (e,) in db.query(Cliente.email).all()}
    nombre_final = nombre or f"Cliente {sigla}"
    cliente = Cliente(
        nombre=nombre_final,
        email=_slug_email(nombre_final, "yudaimportaciones.com", emails_ocupados),
        telefono=telefono,
        pais=pais,
        sigla=sigla,
        hashed_password=hash_password(PASSWORD_PLANTILLA_CONTABLE),
        debe_cambiar_password=True,
        vendedora_id=usuario.id,
        origen=ORIGEN_IMPORTADO_CONTABLE,
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.post("/clientes/importar-contable-uno", response_model=ClienteResponse)
def importar_contable_uno(
    datos: ImportarContableUnoInput,
    usuario: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> ClienteResponse:
    """Importa UN cliente encontrado por /clientes/buscar-contable (búsqueda
    en vivo), a diferencia de /clientes/importar-contable que trae varios de
    la lista fija de una vez."""
    sigla = datos.sigla.strip().upper()
    if db.query(Cliente).filter(Cliente.sigla == sigla).first():
        raise HTTPException(status.HTTP_409_CONFLICT, f"Ya existe un cliente con la sigla {sigla}")

    resultados = buscar_clientes_contable(sigla)
    if resultados is None:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "No se pudo conectar con Yuda Contable")
    encontrado = next((r for r in resultados if r["sigla"].upper() == sigla), None)
    if encontrado is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No se encontró ningún cliente con sigla {sigla} en Yuda Contable")

    cliente = _crear_cliente_desde_contable(
        db, usuario, sigla, encontrado.get("nombre_completo"), encontrado.get("telefono"), encontrado.get("pais")
    )
    return _cliente_response(cliente, usuario, _roles_por_usuario(db, [cliente]))


def _verificar_token_contable(authorization: str | None = Header(None)) -> None:
    """Autoriza la llamada de servidor a servidor desde Yuda Contable (no hay
    sesión de usuario acá): mismo secreto que ya comparten las dos apps para
    la dirección contraria (YUDA_CONTABLE_API_TOKEN)."""
    if not settings.YUDA_CONTABLE_API_TOKEN:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "La integración con Yuda Contable no está configurada")
    esperado = f"Bearer {settings.YUDA_CONTABLE_API_TOKEN}"
    if not authorization or not secrets.compare_digest(authorization, esperado):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autorizado")


@router.post("/clientes/sincronizar-desde-contable", response_model=ClienteResponse)
def sincronizar_cliente_desde_contable(
    datos: SincronizarClienteContableInput,
    db: Session = Depends(get_db),
    _autorizado: None = Depends(_verificar_token_contable),
) -> ClienteResponse:
    """Yuda Contable llama a esto justo después de crear un cliente ahí,
    cuando Marcela elige sincronizarlo de una vez (checkbox en su formulario
    de "Nuevo cliente"). Sin sesión de usuario: se autoriza con un token
    compartido entre las dos apps, no con require_roles.

    Idempotente: si el cliente ya existe acá (mismo sigla, por ejemplo porque
    ya se había importado antes a mano), no lo duplica -solo confirma que
    existe."""
    sigla = datos.sigla.strip().upper()
    admin = db.query(User).filter(User.rol == RolUsuario.admin, User.activo).order_by(User.created_at.asc()).first()
    if admin is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "No hay una cuenta admin activa para asignar el cliente")

    existente = db.query(Cliente).filter(Cliente.sigla == sigla).first()
    if existente:
        return _cliente_response(existente, admin, _roles_por_usuario(db, [existente]))

    cliente = _crear_cliente_desde_contable(db, admin, sigla, datos.nombre, datos.telefono, datos.pais)
    return _cliente_response(cliente, admin, _roles_por_usuario(db, [cliente]))


@router.post("/clientes/importar-contable", response_model=ImportarContableResultado)
def importar_contable(
    datos: ImportarContableInput,
    usuario: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> ImportarContableResultado:
    """Crea un Cliente nuevo por cada sigla elegida que todavía no exista.
    Queda con la propia Marcela como vendedora dueña por defecto: ella decide
    después a quién asignárselo (con lo de la Fase 1). El usuario del portal
    sale del nombre (nombre@yudaimportaciones.com) y la clave es la misma
    para todos (PASSWORD_PLANTILLA_CONTABLE): no se puede avisarle una clave
    distinta a cada uno al importarlos en bloque. El portal los obliga a
    cambiarla en su primer ingreso."""
    por_sigla = {c["sigla"]: c for c in CONTABLE_CLIENTES}
    existentes_sigla = {c.sigla for c in db.query(Cliente).filter(Cliente.sigla.isnot(None)).all()}
    emails_ocupados = {e for (e,) in db.query(Cliente.email).all()}

    creados = 0
    omitidos = 0
    for sigla in datos.siglas:
        datos_contable = por_sigla.get(sigla)
        if datos_contable is None or sigla in existentes_sigla:
            omitidos += 1
            continue
        nombre = datos_contable["nombre"] or f"Cliente {sigla}"
        email = _slug_email(nombre, "yudaimportaciones.com", emails_ocupados)
        cliente = Cliente(
            nombre=nombre,
            email=email,
            telefono=datos_contable["telefono"],
            pais=datos_contable["pais"],
            sigla=sigla,
            hashed_password=hash_password(PASSWORD_PLANTILLA_CONTABLE),
            debe_cambiar_password=True,
            vendedora_id=usuario.id,
            origen=ORIGEN_IMPORTADO_CONTABLE,
        )
        db.add(cliente)
        creados += 1
    db.commit()
    return ImportarContableResultado(creados=creados, omitidos=omitidos)


@router.post("/clientes/desactivar-excepto")
def desactivar_clientes_excepto(
    datos: AsignarVendedorasInput,
    usuario: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    """Limpieza masiva: desactiva TODOS los clientes cuya vendedora dueña no
    esté en la lista dada. No borra nada (los clientes con movimientos no se
    pueden borrar de todas formas); solo los saca de la UI (activo=False)."""
    afectados = (
        db.query(Cliente)
        .filter(Cliente.vendedora_id.notin_(datos.vendedora_ids))
        .all()
    )
    for c in afectados:
        c.activo = False
    db.commit()
    return {"desactivados": len(afectados)}


@router.delete("/clientes/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cliente(
    cliente_id: str,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> None:
    """Elimina un cliente con TODAS sus cotizaciones (enviadas o no), sus pedidos
    generados y su seguimiento. Pierde el acceso al portal.

    Se bloquea si tiene abonos o cobros registrados en su cuenta: esa es
    contabilidad y no se borra sola. En ese caso conviene desactivarlo.
    """
    cliente = _cliente_autorizado(db, cliente_id, usuario)
    _exigir_dueno_o_admin(cliente, usuario)

    if tiene_movimientos_cliente(db, cliente_id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este cliente tiene abonos o cobros registrados en su cuenta. "
            "Desactívalo en lugar de eliminarlo, o pide que se eliminen esos "
            "movimientos primero.",
        )

    sesion_ids = [
        sid for (sid,) in db.query(Sesion.id).filter(Sesion.cliente_id == cliente_id)
    ]
    archivos = borrar_sesiones(db, sesion_ids)
    # Limpieza de la Fase 1 (colaboración): sin esto, un cliente compartido con
    # otra vendedora o con actividad registrada no se puede borrar (viola la FK).
    db.query(ClienteVendedora).filter(ClienteVendedora.cliente_id == cliente_id).delete()
    db.query(ClienteActividad).filter(ClienteActividad.cliente_id == cliente_id).delete()
    db.delete(cliente)
    db.commit()
    limpiar_storage(archivos)


@router.post("/clientes/{cliente_id}/reset-password")
def reset_password_cliente(
    cliente_id: str,
    datos: ResetPasswordRequest,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> dict:
    cliente = _cliente_autorizado(db, cliente_id, usuario)
    _exigir_dueno_o_admin(cliente, usuario)
    nueva = datos.nueva_password.strip()
    if len(nueva) < 6:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contraseña debe tener al menos 6 caracteres")
    cliente.hashed_password = hash_password(nueva)
    # La está poniendo Marcela/la vendedora a propósito (se la comunican
    # ellas mismas), a diferencia de la clave de plantilla de la importación
    # masiva: no hace falta forzar que el cliente la vuelva a cambiar.
    cliente.debe_cambiar_password = False
    # Invalida las sesiones abiertas del cliente con la contraseña vieja.
    cliente.token_version = (cliente.token_version or 0) + 1
    db.commit()
    return {"detail": "Contraseña actualizada"}


@router.post("/clientes/{cliente_id}/estado-cuenta-oficial", response_model=ClienteResponse)
async def subir_estado_cuenta_oficial(
    cliente_id: str,
    archivo: UploadFile,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> ClienteResponse:
    """Marcela (o la vendedora dueña) sube el estado de cuenta real de Yuda
    Contable -PDF o una foto/captura- para que el cliente lo vea en su
    portal. No hay conexión en vivo entre las dos apps: esto reemplaza el
    documento anterior si ya había uno subido."""
    cliente = _cliente_autorizado(db, cliente_id, usuario)

    nombre_original = archivo.filename or ""
    punto = nombre_original.rfind(".")
    extension = nombre_original[punto:].lower() if punto != -1 else ""
    _PERMITIDAS = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    if extension in _PERMITIDAS:
        content_type = _PERMITIDAS[extension]
    elif archivo.content_type in _PERMITIDAS.values():
        content_type = archivo.content_type
        extension = next(k for k, v in _PERMITIDAS.items() if v == content_type)
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Solo se permite PDF o una imagen (JPG, PNG, WEBP)")

    contenido = await archivo.read()
    if len(contenido) > 25 * 1024 * 1024:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El archivo no debe superar 25MB")

    nombre_archivo = f"estado-cuenta-oficial/{cliente_id}-{uuid.uuid4().hex[:8]}{extension}"
    loop = asyncio.get_event_loop()
    try:
        url = await loop.run_in_executor(
            None, lambda: subir_documento(contenido, nombre_archivo, content_type)
        )
    except Exception as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "No se pudo guardar el archivo: el almacenamiento no está disponible. "
            "Intenta de nuevo en unos minutos.",
        ) from exc

    url_anterior = cliente.estado_cuenta_oficial_url
    cliente.estado_cuenta_oficial_url = url
    cliente.estado_cuenta_oficial_actualizado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(cliente)
    if url_anterior:
        borrar_archivos("pedidos", [ruta_desde_url(url_anterior, "pedidos")])
    return _cliente_response(cliente, usuario, _roles_por_usuario(db, [cliente]))


@router.delete("/clientes/{cliente_id}/estado-cuenta-oficial", response_model=ClienteResponse)
def quitar_estado_cuenta_oficial(
    cliente_id: str,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> ClienteResponse:
    """Quita el estado de cuenta oficial (ej. se subió el archivo equivocado)."""
    cliente = _cliente_autorizado(db, cliente_id, usuario)
    url_anterior = cliente.estado_cuenta_oficial_url
    cliente.estado_cuenta_oficial_url = None
    cliente.estado_cuenta_oficial_actualizado_en = None
    db.commit()
    db.refresh(cliente)
    if url_anterior:
        borrar_archivos("pedidos", [ruta_desde_url(url_anterior, "pedidos")])
    return _cliente_response(cliente, usuario, _roles_por_usuario(db, [cliente]))


@router.get("/clientes/{cliente_id}/estado-cuenta-contable/pdf")
def descargar_estado_cuenta_contable(
    cliente_id: str,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> Response:
    """El PDF oficial del estado de cuenta de Yuda Contable, en vivo (no el
    que Marcela sube a mano). 404 si el cliente no tiene sigla vinculada."""
    cliente = _cliente_autorizado(db, cliente_id, usuario)
    if not cliente.sigla:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Este cliente no tiene sigla de Yuda Contable")
    pdf = obtener_pdf_estado_cuenta_contable(cliente.sigla)
    if pdf is None:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "No se pudo traer el estado de cuenta de Yuda Contable")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="estado_cuenta_{cliente.sigla}.pdf"'},
    )


# ──────────────── VÍNCULO COTIZACIÓN ↔ CLIENTE ────────────────


class VincularClienteRequest(BaseModel):
    cliente_id: str | None = None


@router.patch("/sesiones/{sesion_id}/cliente", response_model=SesionResponse)
def vincular_cliente(
    sesion_id: str,
    datos: VincularClienteRequest,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> Sesion:
    """Vincula (o desvincula) una cotización con un cliente del portal"""
    sesion = _sesion_autorizada(db, sesion_id, usuario)

    if datos.cliente_id is None:
        sesion.cliente_id = None
        sesion.enviada_cliente = False
        sesion.fecha_envio_cliente = None
    else:
        _cliente_autorizado(db, datos.cliente_id, usuario)
        sesion.cliente_id = datos.cliente_id

    db.commit()
    db.refresh(sesion)
    return sesion


@router.post("/sesiones/{sesion_id}/enviar-cliente", response_model=SeguimientoResponse)
def enviar_a_cliente(
    sesion_id: str,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> SeguimientoPedido:
    """Marca la cotización como enviada al cliente y crea su seguimiento"""
    sesion = _sesion_autorizada(db, sesion_id, usuario)
    if not sesion.cliente_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Primero asigna un cliente a esta cotización",
        )

    sesion.enviada_cliente = True
    sesion.fecha_envio_cliente = datetime.now()

    seg = db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == sesion_id).first()
    if seg is None:
        ahora = datetime.now(timezone.utc)
        seg = SeguimientoPedido(
            sesion_id=sesion_id,
            estado=ESTADO_INICIAL,
            hitos={
                ESTADO_INICIAL: {
                    "fecha": ahora.date().isoformat(),
                    "nota": None,
                    "ts": ahora.isoformat(),
                }
            },
        )
        db.add(seg)

    db.commit()
    db.refresh(seg)
    return seg


@router.put("/sesiones/{sesion_id}/enviar-a-confirmar", response_model=SesionResponse)
def enviar_a_confirmar(
    sesion_id: str,
    datos: EnviarAConfirmarInput,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> Sesion:
    """La vendedora ajusta las cantidades y le devuelve al cliente la cotización
    para su confirmación final (estado "por confirmar"). El cliente confirma desde
    el portal; recién ahí se puede generar el pedido al proveedor."""
    sesion = _sesion_autorizada(db, sesion_id, usuario)
    items = {i.id: i for i in db.query(Item).filter(Item.sesion_id == sesion_id).all()}
    for linea in datos.items:
        it = items.get(linea.item_id)
        if it is None:
            continue
        it.cantidad_solicitada = linea.cantidad if linea.cantidad and linea.cantidad > 0 else None
    sesion.pedido_estado = PEDIDO_POR_CONFIRMAR
    sesion.pedido_confirmado_at = None
    if sesion.pedido_recibido_at is None:
        sesion.pedido_recibido_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(sesion)
    return sesion


@router.get("/sesiones/{sesion_id}/seguimiento", response_model=SeguimientoResponse)
def obtener_seguimiento(
    sesion_id: str,
    usuario: User = Depends(require_roles("admin", "vendedora", "contadora", "bodega")),
    db: Session = Depends(get_db),
) -> SeguimientoPedido:
    """Seguimiento de una cotización (staff)"""
    _sesion_autorizada(db, sesion_id, usuario)
    seg = db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == sesion_id).first()
    if seg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esta cotización aún no se envió al cliente")
    return seg


@router.put("/sesiones/{sesion_id}/seguimiento", response_model=SeguimientoResponse)
def actualizar_seguimiento(
    sesion_id: str,
    datos: SeguimientoUpdate,
    usuario: User = Depends(require_roles("admin", "vendedora", "bodega")),
    db: Session = Depends(get_db),
) -> SeguimientoPedido:
    """Crea o actualiza el seguimiento del envío de una cotización.

    La vendedora gestiona las etapas hasta que el proveedor recibe el pedido.
    Bodega recibe el pedido confirmado y la orden de compra, los compara y solo
    puede marcar "en bodega" (mercancía recibida y lista para el envío). Cuando
    el contenedor está en camino (naviera, tracking, BL, ETA y las etapas de
    tránsito en adelante) la información es exclusiva de Marcela.
    """
    sesion = _sesion_autorizada(db, sesion_id, usuario)
    es_vendedora = usuario.rol.value == "vendedora"
    es_bodega = usuario.rol.value == "bodega"

    seg = db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == sesion_id).first()
    if seg is None:
        seg = SeguimientoPedido(sesion_id=sesion_id, estado=ESTADO_INICIAL)
        db.add(seg)

    estado_anterior = seg.estado

    # La vendedora no puede mover ni tocar el envío una vez está en tránsito.
    if es_vendedora:
        if estado_anterior not in ESTADOS_VENDEDORA:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Esta cotización ya está en tránsito; la gestiona Marcela",
            )
        if datos.estado not in ESTADOS_VENDEDORA:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "La etapa de envío (en tránsito en adelante) la gestiona Marcela",
            )

    # Bodega solo puede dar el paso "el proveedor recibió" -> "en bodega".
    if es_bodega:
        if estado_anterior != "proveedor_recibio":
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Esta cotización no está lista para que bodega la reciba",
            )
        if datos.estado != "en_bodega":
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Bodega solo puede marcar la mercancía como recibida y enviada",
            )

    # Pasar a "en bodega" exige que TODAS las órdenes a proveedor ya estén
    # revisadas con las cantidades reales — sin importar quién dé el paso.
    # Si esto solo se exigiera cuando el actor es bodega, Marcela podría
    # saltarse la revisión por completo poniendo el estado directamente.
    if datos.estado == "en_bodega":
        ordenes = db.query(PedidoGenerado).filter(PedidoGenerado.sesion_id == sesion_id).all()
        if not ordenes or any(o.revisado_en_bodega_at is None for o in ordenes):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Revisa las cantidades reales de todas las órdenes a proveedor antes de "
                "marcar la mercancía como recibida",
            )

    # Campos que cualquiera del equipo autorizado puede actualizar
    seg.estado = datos.estado
    seg.novedades = datos.novedades
    if datos.hitos is not None:
        # Sella cada hito con fecha+hora la primera vez y conserva el sello original
        # después: el historial de etapas (con sus archivos) se preserva SIEMPRE.
        prev = seg.hitos or {}
        ahora = datetime.now(timezone.utc).isoformat()
        nuevos: dict = {}
        for k, v in datos.hitos.items():
            d = v.model_dump()
            d.pop("ts", None)  # el sello lo maneja el servidor, no el cliente
            d["ts"] = (prev.get(k) or {}).get("ts") or ahora
            nuevos[k] = d
        # La etapa actual siempre queda registrada, aunque no se haya cargado
        # fecha/nota/archivo, para que el historial muestre cuándo se alcanzó.
        if datos.estado not in nuevos:
            nuevos[datos.estado] = {
                "fecha": None,
                "nota": None,
                "adjuntos": None,
                "ts": (prev.get(datos.estado) or {}).get("ts") or ahora,
            }
        seg.hitos = nuevos

    # Al marcar "en bodega" (sea bodega o, si hace falta, Marcela) se le abre
    # al cliente un plazo para aprobar el despacho (por defecto 48h). Se
    # reinicia la aprobación por si esta cotización ya había pasado por acá
    # antes. Sin este plazo, la cotización nunca podría llegar a "en tránsito"
    # (el gate de abajo exige aprobación o plazo vencido, y ninguno de los dos
    # se puede cumplir si esto nunca se fijó).
    if datos.estado == "en_bodega":
        horas = datos.horas_para_aprobar if datos.horas_para_aprobar and datos.horas_para_aprobar > 0 else 48
        seg.aprobacion_limite_at = datetime.now(timezone.utc) + timedelta(hours=horas)
        seg.cliente_aprobo_despacho_at = None

    # Información de envío: solo Marcela (admin). Vendedora y bodega conservan lo cargado.
    if not es_vendedora and not es_bodega:
        # De "en tránsito" en adelante el contenedor ya está despachado.
        en_transito_o_mas = ESTADOS_ENVIO.index(datos.estado) >= ESTADOS_ENVIO.index("en_transito")

        # El monto de la venta (USD) es obligatorio para despachar. Se conserva el
        # ya guardado si esta edición no lo reenvía.
        monto_final = datos.monto_venta if datos.monto_venta is not None else seg.monto_venta
        if en_transito_o_mas and (monto_final is None or monto_final <= 0):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Ingresa el monto de la venta (USD) para marcar el pedido en tránsito",
            )

        # El cliente debe haber aprobado el despacho, o haberse vencido el plazo
        # que bodega le dio, antes de mandar el contenedor por barco.
        if en_transito_o_mas:
            aprobado = seg.cliente_aprobo_despacho_at is not None
            plazo_vencido = (
                seg.aprobacion_limite_at is not None
                and datetime.now(timezone.utc) > seg.aprobacion_limite_at
            )
            if not aprobado and not plazo_vencido:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "El cliente todavía no aprueba el despacho y el plazo que le dio bodega no ha vencido",
                )

        seg.numero_tracking = datos.numero_tracking
        seg.naviera = datos.naviera
        seg.url_tracking = datos.url_tracking
        seg.fecha_eta = datos.fecha_eta
        seg.bl_numero = datos.bl_numero
        seg.bl_pdf_url = datos.bl_pdf_url
        if datos.monto_venta is not None:
            seg.monto_venta = datos.monto_venta

        # Sella el despacho la primera vez que el pedido entra a "en tránsito".
        if en_transito_o_mas and seg.despachado_at is None:
            seg.despachado_at = datetime.now(timezone.utc)

    numero = f"YUDA-{sesion.fecha:%Y%m%d}-{sesion.id[:6].upper()}"

    # Aviso a Marcela cuando la cotización llega a "en bodega" (lista para envío)
    nuevo_en_bodega = datos.estado == ESTADO_DISPARA_AVISO and estado_anterior != ESTADO_DISPARA_AVISO
    if nuevo_en_bodega:
        avisar_listo_para_envio(db, sesion_id, numero, sesion.nombre_cliente, sesion.user_id)

    # Aviso a la vendedora dueña cuando Marcela despacha o entrega su cotización
    if datos.estado in ("en_transito", "entregado") and datos.estado != estado_anterior:
        avisar_envio_a_vendedora(
            db, sesion_id, numero, sesion.nombre_cliente, sesion.user_id, datos.estado
        )

    # El pedido se acaba de mandar a comprar a los proveedores: primer aviso
    # externo al cliente, mucho antes de que bodega reciba nada.
    nuevo_proveedor_recibio = datos.estado == "proveedor_recibio" and estado_anterior != "proveedor_recibio"

    # El cliente ya aprobó (o se venció el plazo) y Marcela despacha el
    # contenedor: de acá en adelante el cliente no recibía NADA propio, solo
    # se le avisaba a la vendedora por dentro. Son las etapas que más
    # ansiedad le dan a un cliente (¿ya salió? ¿ya llegó?) y antes se
    # enteraba solo si le preguntaba a la vendedora.
    nuevo_en_transito = datos.estado == "en_transito" and estado_anterior != "en_transito"
    nuevo_en_destino = datos.estado == "en_destino" and estado_anterior != "en_destino"
    nuevo_entregado = datos.estado == "entregado" and estado_anterior != "entregado"

    # Guarda estos datos ANTES del commit para los avisos externos de abajo (que
    # se mandan después, para no tener llamadas de red lentas con la transacción abierta).
    cliente_a_avisar = None
    if nuevo_en_bodega and sesion.cliente_id and seg.aprobacion_limite_at is not None:
        cliente_a_avisar = db.query(Cliente).filter(Cliente.id == sesion.cliente_id).first()
    plazo_a_avisar = seg.aprobacion_limite_at
    novedades_a_avisar = seg.novedades

    cliente_proveedor = None
    if nuevo_proveedor_recibio and sesion.cliente_id:
        cliente_proveedor = db.query(Cliente).filter(Cliente.id == sesion.cliente_id).first()

    # Bitácora de bodega: con varias personas trabajando el mismo pedido, esto
    # es lo que deja ver quién hizo qué y cuándo.
    if nuevo_proveedor_recibio:
        registrar_actividad_bodega(db, sesion_id, usuario.id, "enviado", "Pedido enviado a bodega")
    if es_bodega and datos.estado == "en_bodega":
        registrar_actividad_bodega(
            db, sesion_id, usuario.id, "confirmado_envio",
            "Bodega confirmó la mercancía recibida y lista para envío",
        )

    cliente_envio = None
    if (nuevo_en_transito or nuevo_en_destino or nuevo_entregado) and sesion.cliente_id:
        cliente_envio = db.query(Cliente).filter(Cliente.id == sesion.cliente_id).first()
    naviera_a_avisar = seg.naviera
    tracking_a_avisar = seg.numero_tracking
    url_tracking_a_avisar = seg.url_tracking
    fecha_eta_a_avisar = seg.fecha_eta

    db.commit()
    db.refresh(seg)

    # Correo (Brevo) + WhatsApp al cliente: fuera de la transacción, para que
    # una llamada de red lenta no deje la conexión a la base ocupada. Incluye
    # la nota que bodega haya escrito (la misma que ve el cliente en el portal).
    if cliente_a_avisar is not None:
        avisar_cliente_aprobar_despacho(
            cliente_a_avisar, sesion_id, numero, plazo_a_avisar, novedades_a_avisar
        )

    if cliente_proveedor is not None:
        avisar_cliente_pedido_en_proveedor(cliente_proveedor, sesion_id, numero)

    if cliente_envio is not None:
        if nuevo_en_transito:
            avisar_cliente_despachado(
                cliente_envio, sesion_id, numero, naviera_a_avisar, tracking_a_avisar,
                url_tracking_a_avisar, fecha_eta_a_avisar,
            )
        if nuevo_en_destino:
            avisar_cliente_en_destino(cliente_envio, sesion_id, numero)
        if nuevo_entregado:
            avisar_cliente_entregado(cliente_envio, sesion_id, numero)

    return seg


@router.post("/sesiones/{sesion_id}/seguimiento/bl-pdf")
async def subir_bl_pdf(
    sesion_id: str,
    archivo: UploadFile,
    usuario: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    """Sube el PDF del BL (solo Marcela) y devuelve su URL para guardarla en el seguimiento"""
    _sesion_autorizada(db, sesion_id, usuario)

    if archivo.content_type != "application/pdf":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El BL debe ser un archivo PDF")

    contenido = await archivo.read()
    if len(contenido) > 25 * 1024 * 1024:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El PDF no debe superar 25MB")

    nombre_archivo = f"bl/{sesion_id}-{uuid.uuid4().hex[:8]}.pdf"
    loop = asyncio.get_event_loop()
    try:
        url = await loop.run_in_executor(None, lambda: subir_pdf(contenido, nombre_archivo))
    except Exception as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "No se pudo guardar el BL: el almacenamiento no está disponible. "
            "Intenta de nuevo en unos minutos.",
        ) from exc
    return {"url": url}


_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# Archivos que se pueden adjuntar a una etapa: extensión -> (tipo, content-type).
# Se valida por extensión y no por el content-type del navegador porque para los
# CSV y los Excel es poco fiable: Windows manda los .csv como
# "application/vnd.ms-excel" y varios navegadores mandan "application/octet-stream".
_ADJ_EXT = {
    ".pdf": ("pdf", "application/pdf"),
    ".jpg": ("imagen", "image/jpeg"),
    ".jpeg": ("imagen", "image/jpeg"),
    ".png": ("imagen", "image/png"),
    ".webp": ("imagen", "image/webp"),
    ".csv": ("csv", "text/csv"),
    ".xls": ("excel", "application/vnd.ms-excel"),
    ".xlsx": ("excel", _XLSX),
}

# Respaldo por content-type para archivos subidos sin extensión en el nombre
_ADJ_CONTENT_TYPE = {
    "application/pdf": ("pdf", ".pdf"),
    "image/jpeg": ("imagen", ".jpg"),
    "image/png": ("imagen", ".png"),
    "image/webp": ("imagen", ".webp"),
    "text/csv": ("csv", ".csv"),
    _XLSX: ("excel", ".xlsx"),
}

_ADJ_NO_SOPORTADO = (
    "Solo se permiten archivos PDF, imágenes (JPG, PNG, WEBP), CSV o Excel (XLS, XLSX)"
)


@router.post("/sesiones/{sesion_id}/seguimiento/adjunto")
async def subir_adjunto_seguimiento(
    sesion_id: str,
    archivo: UploadFile,
    usuario: User = Depends(require_roles("admin", "vendedora", "bodega")),
    db: Session = Depends(get_db),
) -> dict:
    """Sube un PDF, imagen, CSV o Excel para adjuntarlo a una etapa del seguimiento.

    Lo puede subir la vendedora (en sus etapas), bodega (al recibir la mercancía)
    o Marcela; el cliente lo verá en su portal dentro del tracking, y la vendedora
    en el historial de la cotización. Devuelve {url, nombre, tipo} para guardarlo
    en el hito correspondiente.
    """
    _sesion_autorizada(db, sesion_id, usuario)

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
    if len(contenido) > 25 * 1024 * 1024:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El archivo no debe superar 25MB")

    nombre_archivo = f"seguimiento/{sesion_id}-{uuid.uuid4().hex[:8]}{extension}"
    loop = asyncio.get_event_loop()
    try:
        if tipo == "imagen":
            url = await loop.run_in_executor(
                None, lambda: subir_foto(contenido, nombre_archivo, content_type)
            )
        else:
            url = await loop.run_in_executor(
                None, lambda: subir_documento(contenido, nombre_archivo, content_type)
            )
    except Exception as exc:
        # Sin esto el fallo del storage sale como un 500 crudo y la vendedora solo
        # ve "no se pudo adjuntar", sin pista de qué pasó.
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "No se pudo guardar el archivo: el almacenamiento no está disponible. "
            "Intenta de nuevo en unos minutos.",
        ) from exc

    return {"url": url, "nombre": archivo.filename, "tipo": tipo}


# ---------------------------------------------------------------------------
# Cuentas de clientes (estado de cuenta / ledger). Exclusivo de admin y
# contadora: la vendedora no debe ver saldos ni movimientos de dinero.
# ---------------------------------------------------------------------------


def _estado_cuenta(db: Session, cliente: Cliente) -> dict:
    movimientos = (
        db.query(MovimientoCuenta).filter(MovimientoCuenta.cliente_id == cliente.id).all()
    )
    # Pedidos = cotizaciones del cliente (para el nombre/fecha de cada apartado).
    sesiones = db.query(Sesion).filter(Sesion.cliente_id == cliente.id).all()
    return construir_estado_cuenta(cliente, movimientos, sesiones)


def _validar_sesion_del_cliente(db: Session, cliente_id: str, sesion_id: str | None) -> None:
    """El pedido (cotización) asociado a un movimiento debe ser del propio cliente."""
    if sesion_id is None:
        return
    existe = (
        db.query(Sesion)
        .filter(Sesion.id == sesion_id, Sesion.cliente_id == cliente_id)
        .first()
    )
    if existe is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "El pedido no pertenece a este cliente"
        )


def _validar_moneda_pedido(
    db: Session, cliente_id: str, sesion_id: str | None, moneda: str, excluir_id: str | None = None
) -> None:
    """Todos los movimientos de un mismo pedido deben usar la misma moneda."""
    if sesion_id is None:
        return
    q = db.query(MovimientoCuenta).filter(
        MovimientoCuenta.cliente_id == cliente_id,
        MovimientoCuenta.sesion_id == sesion_id,
    )
    if excluir_id:
        q = q.filter(MovimientoCuenta.id != excluir_id)
    otro = q.first()
    if otro is not None and (otro.moneda or "USD") != moneda:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Este pedido ya usa la moneda {otro.moneda}. Usa la misma moneda para el pedido.",
        )


@router.get("/clientes/{cliente_id}/cuenta", response_model=EstadoCuentaResponse)
def obtener_estado_cuenta(
    cliente_id: str,
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> dict:
    """Estado de cuenta del cliente (compras, comisión, abonos, saldo + ledger)"""
    cliente = _cliente_autorizado(db, cliente_id, usuario)
    return _estado_cuenta(db, cliente)


@router.post("/clientes/{cliente_id}/cuenta/excel")
def exportar_estado_cuenta_excel(
    cliente_id: str,
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> Response:
    """Estado de cuenta del cliente en Excel, con el formato del libro contable."""
    cliente = _cliente_autorizado(db, cliente_id, usuario)
    cuenta = _estado_cuenta(db, cliente)
    ahora = datetime.now()
    contenido = generar_estado_cuenta_excel(cuenta, ahora)
    nombre = f"Cuenta_{cliente.nombre}_{ahora:%Y%m%d}.xlsx".replace(" ", "_")
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.post("/clientes/{cliente_id}/cuenta/pdf")
def exportar_estado_cuenta_pdf(
    cliente_id: str,
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> Response:
    """Estado de cuenta del cliente en PDF, para enviarselo tal cual."""
    cliente = _cliente_autorizado(db, cliente_id, usuario)
    cuenta = _estado_cuenta(db, cliente)
    ahora = datetime.now()
    contenido = generar_estado_cuenta_pdf(cuenta, ahora)
    nombre = f"Cuenta_{cliente.nombre}_{ahora:%Y%m%d}.pdf".replace(" ", "_")
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.post(
    "/clientes/{cliente_id}/movimientos",
    response_model=EstadoCuentaResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_movimiento(
    cliente_id: str,
    datos: MovimientoCreate,
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> dict:
    """Agrega un movimiento (envío) a la cuenta del cliente y devuelve la cuenta"""
    cliente = _cliente_autorizado(db, cliente_id, usuario)
    _validar_sesion_del_cliente(db, cliente.id, datos.sesion_id)
    _validar_moneda_pedido(db, cliente.id, datos.sesion_id, datos.moneda)
    comision = (
        datos.comision_yuda
        if datos.comision_yuda is not None
        else calcular_comision(datos.valor_mercancia)
    )
    # Si dijeron cuanto entro y a que tasa, el abono en la moneda de la cuenta se
    # calcula: escribirlo a mano es donde se cuelan los errores de digitacion.
    convertido = convertir_abono(datos.monto_origen, datos.tasa_cambio)
    movimiento = MovimientoCuenta(
        cliente_id=cliente.id,
        sesion_id=datos.sesion_id,
        contenedor_id=datos.contenedor_id,
        moneda=datos.moneda,
        envio=datos.envio,
        fecha=datos.fecha,
        guia=datos.guia,
        descripcion=datos.descripcion,
        valor_mercancia=datos.valor_mercancia,
        comision_yuda=comision,
        abono=convertido if convertido is not None else datos.abono,
        monto_origen=datos.monto_origen,
        moneda_origen=datos.moneda_origen,
        tasa_cambio=datos.tasa_cambio,
        nota=datos.nota,
    )
    db.add(movimiento)
    db.commit()
    return _estado_cuenta(db, cliente)


@router.patch(
    "/clientes/{cliente_id}/movimientos/{movimiento_id}",
    response_model=EstadoCuentaResponse,
)
def actualizar_movimiento(
    cliente_id: str,
    movimiento_id: str,
    datos: MovimientoUpdate,
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> dict:
    """Actualiza un movimiento de la cuenta (campos omitidos no cambian)"""
    cliente = _cliente_autorizado(db, cliente_id, usuario)
    movimiento = (
        db.query(MovimientoCuenta)
        .filter(
            MovimientoCuenta.id == movimiento_id,
            MovimientoCuenta.cliente_id == cliente.id,
        )
        .first()
    )
    if movimiento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Movimiento no encontrado")

    cambios = datos.model_dump(exclude_unset=True)
    # Si se reasigna el pedido, validar que sea del mismo cliente.
    if "sesion_id" in cambios:
        _validar_sesion_del_cliente(db, cliente.id, cambios["sesion_id"])
    # La moneda debe seguir siendo consistente con el pedido tras el cambio.
    if "moneda" in cambios or "sesion_id" in cambios:
        nueva_sesion = cambios.get("sesion_id", movimiento.sesion_id)
        nueva_moneda = cambios.get("moneda", movimiento.moneda or "USD")
        _validar_moneda_pedido(db, cliente.id, nueva_sesion, nueva_moneda, excluir_id=movimiento.id)
    # Si cambió el valor y NO se envió comisión explícita, recalcular la comisión.
    if "valor_mercancia" in cambios and "comision_yuda" not in cambios:
        cambios["comision_yuda"] = calcular_comision(cambios["valor_mercancia"])
    # Lo mismo con el abono: si cambió el monto que entró o la tasa, se recalcula
    # salvo que hayan mandado el abono a mano.
    if ("monto_origen" in cambios or "tasa_cambio" in cambios) and "abono" not in cambios:
        convertido = convertir_abono(
            cambios.get("monto_origen", movimiento.monto_origen),
            cambios.get("tasa_cambio", movimiento.tasa_cambio),
        )
        if convertido is not None:
            cambios["abono"] = convertido
    for campo, valor in cambios.items():
        setattr(movimiento, campo, valor)
    db.commit()
    return _estado_cuenta(db, cliente)


@router.delete(
    "/clientes/{cliente_id}/movimientos/{movimiento_id}",
    response_model=EstadoCuentaResponse,
)
def eliminar_movimiento(
    cliente_id: str,
    movimiento_id: str,
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> dict:
    """Elimina un movimiento de la cuenta del cliente"""
    cliente = _cliente_autorizado(db, cliente_id, usuario)
    movimiento = (
        db.query(MovimientoCuenta)
        .filter(
            MovimientoCuenta.id == movimiento_id,
            MovimientoCuenta.cliente_id == cliente.id,
        )
        .first()
    )
    if movimiento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Movimiento no encontrado")
    db.delete(movimiento)
    db.commit()
    return _estado_cuenta(db, cliente)
