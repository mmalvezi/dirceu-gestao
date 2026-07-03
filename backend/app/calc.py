"""Cálculos derivados das máquinas (via agregação, sem carregar o diário).

CONCEITO (contabilidade do DIRCEU): custo/margem da máquina consideram SÓ o que
sai do bolso dele — diárias origem "bolso" + despesas vinculadas. Repasse EPR e
EPR direto são pagos pela EPR: ficam visíveis (custo_epr) mas FORA da margem.
Horas somam todas (inclusive as próprias): horas são esforço, não dinheiro.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Despesa, DiarioEntrada, DiarioTrabalho

ZERO = Decimal("0")


def _dec(v) -> Decimal:
    return Decimal(str(v)) if v is not None else ZERO


@dataclass
class Agregados:
    horas: Decimal = field(default_factory=lambda: ZERO)
    bolso_diarias: Decimal = field(default_factory=lambda: ZERO)
    despesas: Decimal = field(default_factory=lambda: ZERO)
    repasse: Decimal = field(default_factory=lambda: ZERO)
    epr_direto: Decimal = field(default_factory=lambda: ZERO)

    @property
    def custo_dirceu(self) -> Decimal:
        """O que saiu do bolso do Dirceu: diárias 'bolso' + despesas da máquina."""
        return self.bolso_diarias + self.despesas

    @property
    def custo_epr(self) -> Decimal:
        """Pago pela EPR (repasse + direto) — informativo, fora da margem."""
        return self.repasse + self.epr_direto


def agregados_por_maquina(db: Session, maquina_ids: list[int]) -> dict[int, Agregados]:
    """{maquina_id: Agregados} — trabalhos por origem + despesas vinculadas."""
    if not maquina_ids:
        return {}
    out: dict[int, Agregados] = {}

    rows = (
        db.query(
            DiarioEntrada.maquina_id,
            DiarioTrabalho.origem,
            func.coalesce(func.sum(DiarioTrabalho.valor), 0),
            func.coalesce(func.sum(DiarioTrabalho.horas), 0),
        )
        .join(DiarioTrabalho, DiarioTrabalho.entrada_id == DiarioEntrada.id)
        .filter(DiarioEntrada.maquina_id.in_(maquina_ids))
        .group_by(DiarioEntrada.maquina_id, DiarioTrabalho.origem)
        .all()
    )
    for mid, origem, valor, horas in rows:
        ag = out.setdefault(mid, Agregados())
        ag.horas += _dec(horas)  # todas as origens, inclusive "proprio"
        if origem == "bolso":
            ag.bolso_diarias += _dec(valor)
        elif origem == "repasse":
            ag.repasse += _dec(valor)
        elif origem == "epr_direto":
            ag.epr_direto += _dec(valor)
        # "proprio": só horas (valor é 0)

    desp = (
        db.query(Despesa.maquina_id, func.coalesce(func.sum(Despesa.valor), 0))
        .filter(Despesa.maquina_id.in_(maquina_ids))
        .group_by(Despesa.maquina_id)
        .all()
    )
    for mid, valor in desp:
        out.setdefault(mid, Agregados()).despesas += _dec(valor)

    return out


def ultimos_por_maquina(db: Session, maquina_ids: list[int]) -> dict[int, dict]:
    """{maquina_id: {data, descricao}} da entrada de diário mais recente."""
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


def calcular_margem_pct(empreita, custo_dirceu: Decimal) -> tuple[Decimal, int]:
    """margem = empreita − custo_dirceu; pct = round(custo_dirceu/empreita*100)."""
    empreita = _dec(empreita)
    margem = empreita - custo_dirceu
    pct = int(round(custo_dirceu / empreita * 100)) if empreita > 0 else 0
    return margem, pct
