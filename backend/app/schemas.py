"""Schemas Pydantic da API (cresce a cada fase)."""

from datetime import date, datetime

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


# ----- Financeiro: recebimentos -----

class RecebimentoCreate(BaseModel):
    tipo: str = "adiantamento"
    data: date
    valor: float
    maquina_id: int | None = None
    obs: str | None = None


class RecebimentoUpdate(BaseModel):
    data: date | None = None
    valor: float | None = None
    maquina_id: int | None = None
    obs: str | None = None


class RecebimentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    data: date
    valor: float
    maquina_id: int | None
    maquina_nome: str | None
    status: str
    fechamento_id: int | None
    obs: str | None


# ----- Financeiro: verbas de repasse -----

class RepasseCreate(BaseModel):
    data: date
    valor: float
    obs: str | None = None


class RepasseUpdate(BaseModel):
    data: date | None = None
    valor: float | None = None
    obs: str | None = None


class RepasseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    data: date
    valor: float
    obs: str | None


# ----- Financeiro: totais de origem (aba "Acerto & origens") -----

class FinanceiroTotais(BaseModel):
    periodo_de: date
    periodo_ate: date
    repasse_recebido: float       # Σ verbas de repasse no período
    repasse_pago: float           # Σ trabalhos origem "repasse" no período
    caixa_repasse: float          # saldo acumulado (TOTAL, sem período)
    saido_bolso: float            # Σ trabalhos origem "bolso" no período
    pago_epr_direto: float        # Σ trabalhos origem "epr_direto" no período
    custo_total_ajudantes: float  # soma das três origens no período
    adiantado_aberto: float       # Σ adiantamentos "aberto" (TOTAL, posição atual)


class PagamentoOut(BaseModel):
    """Item da lista "Pagos a ajudantes" (derivada do diário)."""

    data: date
    ajudante_id: int | None
    ajudante_nome: str
    maquina_id: int
    maquina_nome: str
    horas: float
    valor: float
    origem: str


# ----- Fechamento -----

class FechamentoMaquina(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    cliente: str
    empreita: float
    data_finalizacao: date | None


class FechamentoAdiantamento(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    data: date
    valor: float
    maquina_id: int | None
    maquina_nome: str | None


class FechamentoPrevia(BaseModel):
    periodo_de: date
    periodo_ate: date
    maquinas: list[FechamentoMaquina]
    adiantamentos: list[FechamentoAdiantamento]
    total_devido: float
    total_adiantado: float
    saldo: float
    pode_registrar: bool


class FechamentoCreate(BaseModel):
    periodo_de: date
    periodo_ate: date
    obs: str | None = None


class FechamentoOut(BaseModel):
    id: int
    numero: str
    data_geracao: datetime
    periodo_de: date
    periodo_ate: date
    total_devido: float
    total_adiantado: float
    saldo: float
    obs: str | None
    maquinas: list[FechamentoMaquina]


class FechamentoDetalheOut(FechamentoOut):
    adiantamentos: list[FechamentoAdiantamento]
    recebimento_fechamento: RecebimentoOut | None = None


# ----- Dashboard -----

class DashboardPeriodo(BaseModel):
    de: date
    ate: date
    label: str  # ex.: "29/06 a 05/07"


class PagoAjudantes(BaseModel):
    total: float
    repasse: float
    bolso: float
    epr_direto: float


class AdiantadoAbertoKpi(BaseModel):
    total: float
    quantidade: int


class AReceberMaquina(BaseModel):
    nome: str
    valor: float


class AReceberKpi(BaseModel):
    total: float
    maquinas: list[AReceberMaquina]


class DashboardKpis(BaseModel):
    horas_periodo: float
    ajudantes_ativos_periodo: int
    pago_ajudantes: PagoAjudantes
    adiantado_aberto: AdiantadoAbertoKpi
    a_receber: AReceberKpi


class HorasDia(BaseModel):
    dia: str  # seg/ter/qua/qui/sex/sáb/dom
    data: date
    horas: float
    hoje: bool


class MaquinaAndamentoDash(BaseModel):
    id: int
    nome: str
    status: str
    empreita: float
    custo: float
    margem: float
    pct_consumido: int


class Aviso(BaseModel):
    nivel: str  # warn / hot / info
    texto: str


class DashboardOut(BaseModel):
    periodo: DashboardPeriodo
    kpis: DashboardKpis
    horas_por_dia: list[HorasDia]
    maquinas_andamento: list[MaquinaAndamentoDash]
    avisos: list[Aviso]
    resumo_whatsapp: str
