"""Totais de origem do financeiro (aba "Acerto & origens"), via queries agregadas."""

from calendar import monthrange
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import false, func
from sqlalchemy.orm import Session

from app.calc import (
    bolso_periodo,
    repasse_pago_total,
    trabalhos_por_origem_periodo,
)
from app.database import get_db
from app.models import (
    Despesa,
    DiarioEntrada,
    DiarioTrabalho,
    Maquina,
    Recebimento,
    RepasseEntrada,
    Servico,
    ServicoEntrada,
    ServicoTrabalho,
)
from app.schemas import FinanceiroTotais, PagamentoOut, ResultadoOut
from app.security import get_current_user

router = APIRouter(
    prefix="/financeiro",
    tags=["financeiro"],
    dependencies=[Depends(get_current_user)],
)


def _dec(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


def _mes_corrente() -> tuple[date, date]:
    hoje = date.today()
    de = hoje.replace(day=1)
    ate = hoje.replace(day=monthrange(hoje.year, hoje.month)[1])
    return de, ate


@router.get("/pagamentos", response_model=list[PagamentoOut])
def pagamentos(
    de: date | None = None,
    ate: date | None = None,
    ajudante_id: int | None = None,
    origem: str | None = None,
    db: Session = Depends(get_db),
) -> list[PagamentoOut]:
    """Lista "Pagos a ajudantes": trabalhos do diário com máquina, por data DESC."""
    if de is None or ate is None:
        d0, a0 = _mes_corrente()
        de = de or d0
        ate = ate or a0

    saida: list[PagamentoOut] = []

    # Máquinas
    q_maq = (
        db.query(DiarioTrabalho, DiarioEntrada.data, Maquina.id, Maquina.nome)
        .join(DiarioEntrada, DiarioTrabalho.entrada_id == DiarioEntrada.id)
        .join(Maquina, DiarioEntrada.maquina_id == Maquina.id)
        .filter(
            DiarioEntrada.data >= de,
            DiarioEntrada.data <= ate,
            DiarioTrabalho.proprio == false(),  # horas do Dirceu não são pagamento
        )
    )
    if ajudante_id is not None:
        q_maq = q_maq.filter(DiarioTrabalho.ajudante_id == ajudante_id)
    if origem:
        q_maq = q_maq.filter(DiarioTrabalho.origem == origem)
    for t, data, oid, onome in q_maq.all():
        saida.append(PagamentoOut(
            data=data, ajudante_id=t.ajudante_id, ajudante_nome=t.ajudante_nome,
            origem_id=oid, origem_nome=onome, origem_tipo="maquina",
            horas=float(t.horas), valor=float(t.valor), origem=t.origem,
        ))

    # Serviços avulsos
    q_svc = (
        db.query(ServicoTrabalho, ServicoEntrada.data, Servico.id, Servico.descricao)
        .join(ServicoEntrada, ServicoTrabalho.entrada_id == ServicoEntrada.id)
        .join(Servico, ServicoEntrada.servico_id == Servico.id)
        .filter(
            ServicoEntrada.data >= de,
            ServicoEntrada.data <= ate,
            ServicoTrabalho.proprio == false(),
        )
    )
    if ajudante_id is not None:
        q_svc = q_svc.filter(ServicoTrabalho.ajudante_id == ajudante_id)
    if origem:
        q_svc = q_svc.filter(ServicoTrabalho.origem == origem)
    for t, data, oid, onome in q_svc.all():
        saida.append(PagamentoOut(
            data=data, ajudante_id=t.ajudante_id, ajudante_nome=t.ajudante_nome,
            origem_id=oid, origem_nome=onome, origem_tipo="servico",
            horas=float(t.horas), valor=float(t.valor), origem=t.origem,
        ))

    saida.sort(key=lambda p: p.data, reverse=True)
    return saida


@router.get("/totais", response_model=FinanceiroTotais)
def totais(
    de: date | None = None,
    ate: date | None = None,
    db: Session = Depends(get_db),
) -> FinanceiroTotais:
    # Sem período completo → mês corrente.
    if de is None or ate is None:
        d0, a0 = _mes_corrente()
        de = de or d0
        ate = ate or a0

    # Trabalhos por origem no período (máquinas + serviços).
    por_origem = trabalhos_por_origem_periodo(db, de, ate)
    repasse_pago = por_origem.get("repasse", (Decimal("0"),))[0]
    saido_bolso = por_origem.get("bolso", (Decimal("0"),))[0]
    pago_epr_direto = por_origem.get("epr_direto", (Decimal("0"),))[0]
    custo_total = repasse_pago + saido_bolso + pago_epr_direto

    # Verbas de repasse recebidas no período.
    repasse_recebido = _dec(
        db.query(func.coalesce(func.sum(RepasseEntrada.valor), 0))
        .filter(RepasseEntrada.data >= de, RepasseEntrada.data <= ate)
        .scalar()
    )

    # Caixa de repasse = saldo ACUMULADO (sem período): tudo recebido − tudo pago em repasse.
    repasse_recebido_total = _dec(
        db.query(func.coalesce(func.sum(RepasseEntrada.valor), 0)).scalar()
    )
    caixa_repasse = repasse_recebido_total - repasse_pago_total(db)

    # Adiantamentos em aberto = posição atual (sem período).
    adiantado_aberto = _dec(
        db.query(func.coalesce(func.sum(Recebimento.valor), 0))
        .filter(Recebimento.tipo == "adiantamento", Recebimento.status == "aberto")
        .scalar()
    )

    despesas_periodo = _dec(
        db.query(func.coalesce(func.sum(Despesa.valor), 0))
        .filter(Despesa.data >= de, Despesa.data <= ate)
        .scalar()
    )

    return FinanceiroTotais(
        periodo_de=de,
        periodo_ate=ate,
        repasse_recebido=float(repasse_recebido),
        repasse_pago=float(repasse_pago),
        caixa_repasse=float(caixa_repasse),
        saido_bolso=float(saido_bolso),
        pago_epr_direto=float(pago_epr_direto),
        custo_total_ajudantes=float(custo_total),
        adiantado_aberto=float(adiantado_aberto),
        despesas_periodo=float(despesas_periodo),
    )


@router.get("/resultado", response_model=ResultadoOut)
def resultado(de: date, ate: date, db: Session = Depends(get_db)) -> ResultadoOut:
    """Resultado do período (ganho real): entradas − (bolso + despesas).

    Repasse e EPR direto ficam FORA — não são dinheiro do Dirceu.
    """
    if de > ate:
        raise HTTPException(status_code=422, detail="Período inválido: 'de' deve ser <= 'ate'.")

    total_entradas = _dec(
        db.query(func.coalesce(func.sum(Recebimento.valor), 0))
        .filter(Recebimento.data >= de, Recebimento.data <= ate)
        .scalar()
    )
    total_bolso = bolso_periodo(db, de, ate)  # máquinas + serviços
    total_despesas = _dec(
        db.query(func.coalesce(func.sum(Despesa.valor), 0))
        .filter(Despesa.data >= de, Despesa.data <= ate)
        .scalar()
    )
    total_saidas = total_bolso + total_despesas
    return ResultadoOut(
        periodo_de=de,
        periodo_ate=ate,
        total_entradas=float(total_entradas),
        total_bolso=float(total_bolso),
        total_despesas=float(total_despesas),
        total_saidas=float(total_saidas),
        resultado=float(total_entradas - total_saidas),
    )
