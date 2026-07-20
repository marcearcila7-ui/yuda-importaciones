from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.database import get_db
from app.models.contenedor import Contenedor
from app.models.user import User
from app.schemas.contenedor import (
    ContenedorCreate,
    ContenedorResponse,
    ContenedorUpdate,
)

# Se monta en main.py bajo /api/v1 (sin prefijo propio).
# La contadora y el admin gestionan los contenedores/embarques y su TRM.
router = APIRouter(tags=["contenedores"])


def _obtener_contenedor(db: Session, contenedor_id: str) -> Contenedor:
    contenedor = db.query(Contenedor).filter(Contenedor.id == contenedor_id).first()
    if contenedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado")
    return contenedor


@router.get("/contenedores", response_model=list[ContenedorResponse])
def listar_contenedores(
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> list[Contenedor]:
    """Lista los contenedores/embarques, del más reciente al más antiguo"""
    return db.query(Contenedor).order_by(Contenedor.created_at.desc()).all()


@router.get("/contenedores/{contenedor_id}", response_model=ContenedorResponse)
def obtener_contenedor(
    contenedor_id: str,
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> Contenedor:
    """Devuelve un contenedor por id"""
    return _obtener_contenedor(db, contenedor_id)


@router.post(
    "/contenedores",
    response_model=ContenedorResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_contenedor(
    datos: ContenedorCreate,
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> Contenedor:
    """Crea un contenedor/embarque con su TRM (tasa RMB→USD) manual"""
    contenedor = Contenedor(
        codigo=datos.codigo.strip(),
        trm_usd=datos.trm_usd,
        fecha=datos.fecha,
        estado=datos.estado,
        notas=datos.notas,
    )
    db.add(contenedor)
    db.commit()
    db.refresh(contenedor)
    return contenedor


@router.patch("/contenedores/{contenedor_id}", response_model=ContenedorResponse)
def actualizar_contenedor(
    contenedor_id: str,
    datos: ContenedorUpdate,
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> Contenedor:
    """Actualiza los campos enviados de un contenedor (los omitidos no cambian)"""
    contenedor = _obtener_contenedor(db, contenedor_id)

    cambios = datos.model_dump(exclude_unset=True)
    if "codigo" in cambios and cambios["codigo"] is not None:
        cambios["codigo"] = cambios["codigo"].strip()
    for campo, valor in cambios.items():
        setattr(contenedor, campo, valor)

    db.commit()
    db.refresh(contenedor)
    return contenedor


@router.delete("/contenedores/{contenedor_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_contenedor(
    contenedor_id: str,
    usuario: User = Depends(require_roles("admin", "contadora")),
    db: Session = Depends(get_db),
) -> None:
    """Elimina un contenedor. Solo debería usarse cuando no tiene movimientos asociados."""
    contenedor = _obtener_contenedor(db, contenedor_id)
    db.delete(contenedor)
    db.commit()
