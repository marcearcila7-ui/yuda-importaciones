from sqlalchemy.orm import Session

from app.models.notificacion import TIPO_LISTO_PARA_ENVIO, Notificacion
from app.models.user import RolUsuario, User


def avisar_listo_para_envio(db: Session, sesion_id: str, numero: str, cliente: str) -> None:
    """Crea un aviso para cada admin (Marcela): la cotización está lista para que
    cargue la naviera y el BL. Evita duplicar si ya hay un aviso sin leer de esta
    cotización para ese admin.
    """
    admins = db.query(User).filter(User.rol == RolUsuario.admin, User.activo).all()
    for admin in admins:
        ya_existe = (
            db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == admin.id,
                Notificacion.sesion_id == sesion_id,
                Notificacion.tipo == TIPO_LISTO_PARA_ENVIO,
                Notificacion.leida.is_(False),
            )
            .first()
        )
        if ya_existe:
            continue
        db.add(
            Notificacion(
                usuario_id=admin.id,
                sesion_id=sesion_id,
                tipo=TIPO_LISTO_PARA_ENVIO,
                titulo="Cotización lista para envío",
                mensaje=(
                    f"La cotización {numero} de {cliente} está en bodega. "
                    "Es momento de cargar la naviera y el BL."
                ),
            )
        )
