"""Cálculos derivados das máquinas (via agregação, sem carregar o diário).

CONCEITO (contabilidade do DIRCEU): custo/margem da máquina consideram SÓ o que
sai do bolso dele — diárias origem "bolso" + despesas vinculadas. Repasse EPR e
EPR direto são pagos pela EPR: ficam visíveis (custo_epr) mas FORA da margem.
Horas somam todas (inclusive as próprias): horas são esforço, não dinheiro.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import false, func
from sqlalchemy.orm import Session

from app.models import (
    Despesa,
    DiarioEntrada,
    DiarioTrabalho,
    ServicoEntrada,
    ServicoTrabalho,
)

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


def agregados_por_servico(db: Session, servico_ids: list[int]) -> dict[int, Agregados]:
    """{servico_id: Agregados} — trabalhos por origem + despesas vinculadas ao serviço."""
    if not servico_ids:
        return {}
    out: dict[int, Agregados] = {}

    rows = (
        db.query(
            ServicoEntrada.servico_id,
            ServicoTrabalho.origem,
            func.coalesce(func.sum(ServicoTrabalho.valor), 0),
            func.coalesce(func.sum(ServicoTrabalho.horas), 0),
        )
        .join(ServicoTrabalho, ServicoTrabalho.entrada_id == ServicoEntrada.id)
        .filter(ServicoEntrada.servico_id.in_(servico_ids))
        .group_by(ServicoEntrada.servico_id, ServicoTrabalho.origem)
        .all()
    )
    for sid, origem, valor, horas in rows:
        ag = out.setdefault(sid, Agregados())
        ag.horas += _dec(horas)
        if origem == "bolso":
            ag.bolso_diarias += _dec(valor)
        elif origem == "repasse":
            ag.repasse += _dec(valor)
        elif origem == "epr_direto":
            ag.epr_direto += _dec(valor)

    desp = (
        db.query(Despesa.servico_id, func.coalesce(func.sum(Despesa.valor), 0))
        .filter(Despesa.servico_id.in_(servico_ids))
        .group_by(Despesa.servico_id)
        .all()
    )
    for sid, valor in desp:
        out.setdefault(sid, Agregados()).despesas += _dec(valor)

    return out


def ultimos_por_servico(db: Session, servico_ids: list[int]) -> dict[int, dict]:
    """{servico_id: {data, descricao}} da entrada de diário mais recente."""
    if not servico_ids:
        return {}
    rows = (
        db.query(ServicoEntrada.servico_id, ServicoEntrada.data, ServicoEntrada.descricao)
        .filter(ServicoEntrada.servico_id.in_(servico_ids))
        .order_by(ServicoEntrada.data.desc(), ServicoEntrada.id.desc())
        .all()
    )
    out: dict[int, dict] = {}
    for sid, data, descricao in rows:
        if sid not in out:
            out[sid] = {"data": data, "descricao": descricao}
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


# ---- Agregados de diário no PERÍODO, abrangendo máquinas E serviços ----
# (um pagamento/hora é o mesmo, tenha sido numa empreita ou num serviço avulso)

_DIARIOS = (
    (DiarioEntrada, DiarioTrabalho),
    (ServicoEntrada, ServicoTrabalho),
)


def trabalhos_por_origem_periodo(db, de, ate) -> dict[str, tuple[Decimal, Decimal]]:
    """{origem: (valor, horas)} somando os dois diários no período."""
    out: dict[str, list[Decimal]] = {}
    for Ent, Trab in _DIARIOS:
        rows = (
            db.query(
                Trab.origem,
                func.coalesce(func.sum(Trab.valor), 0),
                func.coalesce(func.sum(Trab.horas), 0),
            )
            .join(Ent, Trab.entrada_id == Ent.id)
            .filter(Ent.data >= de, Ent.data <= ate)
            .group_by(Trab.origem)
            .all()
        )
        for origem, valor, horas in rows:
            acc = out.setdefault(origem, [ZERO, ZERO])
            acc[0] += _dec(valor)
            acc[1] += _dec(horas)
    return {o: (v, h) for o, (v, h) in out.items()}


def horas_por_data_periodo(db, de, ate) -> dict:
    """{data: horas} somando os dois diários no período."""
    out: dict = {}
    for Ent, Trab in _DIARIOS:
        rows = (
            db.query(Ent.data, func.coalesce(func.sum(Trab.horas), 0))
            .join(Trab, Trab.entrada_id == Ent.id)
            .filter(Ent.data >= de, Ent.data <= ate)
            .group_by(Ent.data)
            .all()
        )
        for data, horas in rows:
            out[data] = out.get(data, ZERO) + _dec(horas)
    return out


def ajudantes_distintos_periodo(db, de, ate) -> int:
    """Nº de ajudantes distintos (exclui o Dirceu/proprio) nos dois diários."""
    nomes: set[str] = set()
    for Ent, Trab in _DIARIOS:
        rows = (
            db.query(Trab.ajudante_nome)
            .join(Ent, Trab.entrada_id == Ent.id)
            .filter(Ent.data >= de, Ent.data <= ate, Trab.proprio == false())
            .distinct()
            .all()
        )
        nomes.update(n for (n,) in rows)
    return len(nomes)


def bolso_periodo(db, de, ate) -> Decimal:
    """Σ diárias origem 'bolso' nos dois diários (saída real do Dirceu no período)."""
    return trabalhos_por_origem_periodo(db, de, ate).get("bolso", (ZERO, ZERO))[0]


def repasse_pago_total(db) -> Decimal:
    """Σ diárias 'repasse' acumuladas (sem período), nos dois diários."""
    total = ZERO
    for _, Trab in _DIARIOS:
        total += _dec(
            db.query(func.coalesce(func.sum(Trab.valor), 0))
            .filter(Trab.origem == "repasse")
            .scalar()
        )
    return total
