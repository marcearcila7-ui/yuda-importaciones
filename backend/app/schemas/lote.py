from typing import Optional

from pydantic import BaseModel, ConfigDict


class LoteCreado(BaseModel):
    lote_id: str


class LoteItemInfo(BaseModel):
    id: str
    foto_url: str
    estado: str
    datos: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class LoteEstado(BaseModel):
    id: str
    sesion_id: str
    estado: str
    total: int
    procesadas: int
    items: list[LoteItemInfo]


class LoteActivo(BaseModel):
    lote_id: Optional[str] = None
    estado: Optional[str] = None
