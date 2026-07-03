"""Totais de origem do financeiro (aba "Acerto & origens"), via queries agregadas."""

from calendar import monthrange
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DiarioEntrada, DiarioTrabalho, Recebimento, RepasseEntrada
from app.schemas import FinanceiroTotais
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

    # Trabalhos por origem no período (JOIN para filtrar pela DATA DA ENTRADA).
    rows = (
        db.query(
            DiarioTrabalho.origem,
            func.coalesce(func.sum(DiarioTrabalho.valor), 0),
        )
        .join(DiarioEntrada, DiarioTrabalho.entrada_id == DiarioEntrada.id)
        .filter(DiarioEntrada.data >= de, DiarioEntrada.data <= ate)
        .group_by(DiarioTrabalho.origem)
        .all()
    )
    por_origem = {origem: _dec(valor) for origem, valor in rows}
    repasse_pago = por_origem.get("repasse", Decimal("0"))
    saido_bolso = por_origem.get("bolso", Decimal("0"))
    pago_epr_direto = por_origem.get("epr_direto", Decimal("0"))
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
    repasse_pago_total = _dec(
        db.query(func.coalesce(func.sum(DiarioTrabalho.valor), 0))
        .filter(DiarioTrabalho.origem == "repasse")
        .scalar()
    )
    caixa_repasse = repasse_recebido_total - repasse_pago_total

    # Adiantamentos em aberto = posição atual (sem período).
    adiantado_aberto = _dec(
        db.query(func.coalesce(func.sum(Recebimento.valor), 0))
        .filter(Recebimento.tipo == "adiantamento", Recebimento.status == "aberto")
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
    )
