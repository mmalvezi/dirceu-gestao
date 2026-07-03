"""Cálculos derivados das máquinas (custo/horas via agregação, sem carregar o diário)."""

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import DiarioEntrada, DiarioTrabalho


def _dec(v) -> Decimal:
    """Converte valor agregado (Decimal/float/int/None) em Decimal seguro."""
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def agregados_por_maquina(
    db: Session, maquina_ids: list[int]
) -> dict[int, tuple[Decimal, Decimal]]:
    """Retorna {maquina_id: (custo, horas)} somando os trabalhos do diário via GROUP BY."""
    if not maquina_ids:
        return {}
    rows = (
        db.query(
            DiarioEntrada.maquina_id,
            func.coalesce(func.sum(DiarioTrabalho.valor), 0),
            func.coalesce(func.sum(DiarioTrabalho.horas), 0),
        )
        .join(DiarioTrabalho, DiarioTrabalho.entrada_id == DiarioEntrada.id)
        .filter(DiarioEntrada.maquina_id.in_(maquina_ids))
        .group_by(DiarioEntrada.maquina_id)
        .all()
    )
    return {mid: (_dec(custo), _dec(horas)) for mid, custo, horas in rows}


def ultimos_por_maquina(db: Session, maquina_ids: list[int]) -> dict[int, dict]:
    """Retorna {maquina_id: {data, descricao}} da entrada de diário mais recente."""
    if not maquina_ids:
        return {}
    rows = (
        db.query(
            DiarioEntrada.maquina_id,
            DiarioEntrada.data,
            DiarioEntrada.descricao,
        )
        .filter(DiarioEntrada.maquina_id.in_(maquina_ids))
        .order_by(DiarioEntrada.data.desc(), DiarioEntrada.id.desc())
        .all()
    )
    out: dict[int, dict] = {}
    for mid, data, descricao in rows:
        if mid not in out:  # primeiro visto = mais recente (ordenação desc)
            out[mid] = {"data": data, "descricao": descricao}
    return out


def calcular_margem_pct(empreita: Decimal, custo: Decimal) -> tuple[Decimal, int]:
    """margem = empreita - custo; pct_consumido = round(custo/empreita*100) (0 se empreita<=0)."""
    empreita = _dec(empreita)
    margem = empreita - custo
    pct = int(round(custo / empreita * 100)) if empreita > 0 else 0
    return margem, pct
