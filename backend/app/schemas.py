"""Schemas Pydantic da API (cresce a cada fase)."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


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


# ----- Ajudantes -----

class AjudanteCreate(BaseModel):
    nome: str
    telefone: str | None = None
    valor_hora_padrao: float | None = None
    obs: str | None = None


class AjudanteUpdate(BaseModel):
    nome: str | None = None
    telefone: str | None = None
    valor_hora_padrao: float | None = None
    obs: str | None = None
    ativo: bool | None = None


class AjudanteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    telefone: str | None
    valor_hora_padrao: float | None
    obs: str | None
    ativo: bool


# ----- Máquinas -----

class MaquinaCreate(BaseModel):
    nome: str
    cliente: str
    empreita: float
    data_inicio: date
    obs: str | None = None


class MaquinaUpdate(BaseModel):
    nome: str | None = None
    cliente: str | None = None
    empreita: float | None = None
    status: str | None = None
    data_inicio: date | None = None
    data_finalizacao: date | None = None
    obs: str | None = None


class UltimoLancamento(BaseModel):
    data: date
    descricao: str


class MaquinaOut(BaseModel):
    id: int
    nome: str
    cliente: str
    empreita: float
    status: str
    data_inicio: date
    data_finalizacao: date | None = None
    obs: str | None = None
    custo: float
    horas: float
    margem: float
    pct_consumido: int
    ultimo_lancamento: UltimoLancamento | None = None


# ----- Diário de obra -----

class TrabalhoIn(BaseModel):
    ajudante_id: int | None = None
    ajudante_nome: str | None = None
    horas: float = Field(gt=0)
    valor: float = Field(ge=0)
    origem: str


class TrabalhoOut(BaseModel):
    id: int
    ajudante_id: int | None
    ajudante_nome: str
    horas: float
    valor: float
    origem: str


class DiarioEntradaIn(BaseModel):
    data: date
    descricao: str
    trabalhos: list[TrabalhoIn] = []


class DiarioEntradaOut(BaseModel):
    id: int
    maquina_id: int
    data: date
    descricao: str
    trabalhos: list[TrabalhoOut]
    total_horas: float
    total_valor: float


class DiarioEntradaSalvaOut(DiarioEntradaOut):
    """Resposta de POST/PUT: inclui o aviso de máquina finalizada (senão null)."""

    aviso: str | None = None


class MaquinaDetalheOut(MaquinaOut):
    diario: list[DiarioEntradaOut] = []
