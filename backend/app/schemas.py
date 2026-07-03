"""Schemas Pydantic da API (cresce a cada fase)."""

from pydantic import BaseModel, ConfigDict


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class ConfigOut(BaseModel):
    nome_exibicao: str
    telefone: str | None = None
    logo_filename: str | None = None
    logo_url: str | None = None


class ConfigUpdate(BaseModel):
    nome_exibicao: str | None = None
    telefone: str | None = None
