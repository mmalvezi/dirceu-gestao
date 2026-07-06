"""Rotas dos relatórios PDF (todas protegidas). Monta os dados e delega ao app/pdf.py."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import false, func
from sqlalchemy.orm import Session, selectinload

from app.calc import Agregados, agregados_por_maquina, calcular_margem_pct
from app.database import get_db
from app.models import (
    Ajudante,
    Despesa,
    DiarioEntrada,
    DiarioTrabalho,
    Fechamento,
    Maquina,
    Recebimento,
    RepasseEntrada,
    Servico,
)
from app.pdf import (
    pdf_ajudantes,
    pdf_entradas,
    pdf_fechamento,
    pdf_maquina,
    pdf_maquinas_consolidado,
    pdf_periodo,
    pdf_resultado,
    slug,
)
from app.routers.config import get_config
from app.routers.fechamentos import _calcular_previa
from app.security import get_current_user
from app.utils import data_curta

router = APIRouter(prefix="/pdf", tags=["pdf"], dependencies=[Depends(get_current_user)])


def _dec(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


def _resp(pdf, filename: str) -> Response:
    return Response(
        content=bytes(pdf.output()),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


def _periodo_ok(de: date, ate: date) -> None:
    if de > ate:
        raise HTTPException(status_code=422, detail="Período inválido: 'de' deve ser <= 'ate'.")


# -------- 1) dossiê da máquina --------

@router.get("/maquina/{maquina_id}")
def rel_maquina(maquina_id: int, db: Session = Depends(get_db)) -> Response:
    maquina = db.get(Maquina, maquina_id)
    if maquina is None:
        raise HTTPException(status_code=404, detail="Máquina não encontrada")

    entradas = (
        db.query(DiarioEntrada)
        .filter(DiarioEntrada.maquina_id == maquina_id)
        .options(selectinload(DiarioEntrada.trabalhos))
        .order_by(DiarioEntrada.data.asc(), DiarioEntrada.id.asc())
        .all()
    )
    ag = agregados_por_maquina(db, [maquina_id]).get(maquina_id, Agregados())
    margem, pct = calcular_margem_pct(maquina.empreita, ag.custo_dirceu)
    pdf = pdf_maquina(get_config(db), maquina, entradas, ag, margem, pct)
    return _resp(pdf, f"maquina-{slug(maquina.nome)}.pdf")


# -------- 1b) consolidado de máquinas por status --------

_ROTULO_STATUS = {"todas": "Todas", "andamento": "Em andamento",
                  "finalizada": "Finalizadas", "fechada": "Fechadas"}


@router.get("/maquinas")
def rel_maquinas(status: str = "todas", db: Session = Depends(get_db)) -> Response:
    if status not in _ROTULO_STATUS:
        raise HTTPException(status_code=422, detail="Status inválido")
    query = db.query(Maquina)
    if status != "todas":
        query = query.filter(Maquina.status == status)
    maquinas = query.order_by(Maquina.data_inicio.desc(), Maquina.id.desc()).all()
    if not maquinas:
        raise HTTPException(status_code=404, detail="Nenhuma máquina neste status.")

    ags = agregados_por_maquina(db, [m.id for m in maquinas])
    blocos, totais = [], {"empreita": Decimal("0"), "custo_dirceu": Decimal("0"),
                          "epr": Decimal("0"), "margem": Decimal("0"), "horas": Decimal("0")}
    for m in maquinas:
        ag = ags.get(m.id, Agregados())
        margem, pct = calcular_margem_pct(m.empreita, ag.custo_dirceu)
        entradas = (
            db.query(DiarioEntrada)
            .filter(DiarioEntrada.maquina_id == m.id)
            .options(selectinload(DiarioEntrada.trabalhos))
            .order_by(DiarioEntrada.data.desc(), DiarioEntrada.id.desc())
            .limit(10)
            .all()
        )
        total_entradas = (
            db.query(func.count(DiarioEntrada.id))
            .filter(DiarioEntrada.maquina_id == m.id)
            .scalar() or 0
        )
        blocos.append({"maquina": m, "ag": ag, "margem": margem, "pct": pct,
                       "entradas": entradas, "mais_n": max(0, total_entradas - 10)})
        totais["empreita"] += _dec(m.empreita)
        totais["custo_dirceu"] += ag.custo_dirceu
        totais["epr"] += ag.custo_epr
        totais["margem"] += margem
        totais["horas"] += ag.horas

    pdf = pdf_maquinas_consolidado(get_config(db), _ROTULO_STATUS[status], blocos, totais)
    return _resp(pdf, f"maquinas-{status}.pdf")


# -------- 2) consolidado do período --------

@router.get("/periodo")
def rel_periodo(de: date, ate: date, db: Session = Depends(get_db)) -> Response:
    _periodo_ok(de, ate)
    rows = (
        db.query(
            DiarioEntrada.maquina_id,
            DiarioTrabalho.origem,
            func.coalesce(func.sum(DiarioTrabalho.valor), 0),
            func.coalesce(func.sum(DiarioTrabalho.horas), 0),
        )
        .join(DiarioTrabalho, DiarioTrabalho.entrada_id == DiarioEntrada.id)
        .filter(DiarioEntrada.data >= de, DiarioEntrada.data <= ate)
        .group_by(DiarioEntrada.maquina_id, DiarioTrabalho.origem)
        .all()
    )
    def novo_bloco():
        return {"horas": Decimal("0"), "bolso": Decimal("0"), "despesas": Decimal("0"),
                "epr": Decimal("0")}

    por_maquina: dict[int, dict] = {}
    for mid, origem, valor, horas in rows:
        b = por_maquina.setdefault(mid, novo_bloco())
        b["horas"] += _dec(horas)
        if origem == "bolso":
            b["bolso"] += _dec(valor)
        elif origem in ("repasse", "epr_direto"):
            b["epr"] += _dec(valor)  # pago pela EPR — fora da margem

    # despesas vinculadas a máquinas no período também são atividade
    desp_rows = (
        db.query(Despesa.maquina_id, func.coalesce(func.sum(Despesa.valor), 0))
        .filter(Despesa.maquina_id.isnot(None), Despesa.data >= de, Despesa.data <= ate)
        .group_by(Despesa.maquina_id)
        .all()
    )
    for mid, valor in desp_rows:
        por_maquina.setdefault(mid, novo_bloco())["despesas"] += _dec(valor)

    for b in por_maquina.values():
        b["custo_dirceu"] = b["bolso"] + b["despesas"]

    maquinas = {
        m.id: m
        for m in db.query(Maquina).filter(Maquina.id.in_(por_maquina.keys())).all()
    }
    blocos = [
        {"maquina": maquinas[mid], **b}
        for mid, b in sorted(por_maquina.items(), key=lambda kv: -float(kv[1]["custo_dirceu"]))
        if mid in maquinas
    ]
    gerais = {
        campo: sum((b[campo] for b in blocos), Decimal("0"))
        for campo in ("horas", "bolso", "despesas", "custo_dirceu", "epr")
    }
    pdf = pdf_periodo(get_config(db), de, ate, blocos, gerais)
    return _resp(pdf, f"periodo-{de.isoformat()}-a-{ate.isoformat()}.pdf")


# -------- 3) saídas — ajudantes --------

@router.get("/ajudantes")
def rel_ajudantes(
    de: date, ate: date, ajudante_id: int | None = None, db: Session = Depends(get_db)
) -> Response:
    _periodo_ok(de, ate)
    if ajudante_id is not None and db.get(Ajudante, ajudante_id) is None:
        raise HTTPException(status_code=404, detail="Ajudante não encontrado")

    query = (
        db.query(DiarioTrabalho, DiarioEntrada.data, Maquina.nome)
        .join(DiarioEntrada, DiarioTrabalho.entrada_id == DiarioEntrada.id)
        .join(Maquina, DiarioEntrada.maquina_id == Maquina.id)
        .filter(
            DiarioEntrada.data >= de,
            DiarioEntrada.data <= ate,
            DiarioTrabalho.proprio == false(),  # horas próprias não são saída
        )
    )
    if ajudante_id is not None:
        query = query.filter(DiarioTrabalho.ajudante_id == ajudante_id)
    rows = query.order_by(DiarioEntrada.data.asc(), DiarioTrabalho.id.asc()).all()

    grupos_map: dict[str, dict] = {}
    for t, data_entrada, maquina_nome in rows:
        g = grupos_map.setdefault(
            t.ajudante_nome,
            {"nome": t.ajudante_nome, "itens": [], "horas": Decimal("0"), "valor": Decimal("0")},
        )
        g["itens"].append(
            {"data": data_entrada, "maquina": maquina_nome, "horas": t.horas,
             "origem": t.origem, "valor": t.valor}
        )
        g["horas"] += _dec(t.horas)
        g["valor"] += _dec(t.valor)
    grupos = sorted(grupos_map.values(), key=lambda g: g["nome"].lower())
    total_geral = sum((g["valor"] for g in grupos), Decimal("0"))

    pdf = pdf_ajudantes(get_config(db), de, ate, grupos, total_geral)
    sufixo = f"-{slug(grupos[0]['nome'])}" if (ajudante_id is not None and grupos) else ""
    return _resp(pdf, f"ajudantes-{de.isoformat()}-a-{ate.isoformat()}{sufixo}.pdf")


# -------- 4) entradas — recebimentos --------

@router.get("/entradas")
def rel_entradas(de: date, ate: date, db: Session = Depends(get_db)) -> Response:
    _periodo_ok(de, ate)
    recebimentos = (
        db.query(Recebimento)
        .filter(Recebimento.data >= de, Recebimento.data <= ate)
        .order_by(Recebimento.data.asc(), Recebimento.id.asc())
        .all()
    )
    total_receb = sum((_dec(r.valor) for r in recebimentos), Decimal("0"))
    repasses = (
        db.query(RepasseEntrada)
        .filter(RepasseEntrada.data >= de, RepasseEntrada.data <= ate)
        .order_by(RepasseEntrada.data.asc(), RepasseEntrada.id.asc())
        .all()
    )
    total_repasses = sum((_dec(v.valor) for v in repasses), Decimal("0"))
    pdf = pdf_entradas(get_config(db), de, ate, recebimentos, total_receb, repasses, total_repasses)
    return _resp(pdf, f"entradas-{de.isoformat()}-a-{ate.isoformat()}.pdf")


# -------- 5) resultado do período (ganho real) --------

@router.get("/resultado")
def rel_resultado(de: date, ate: date, db: Session = Depends(get_db)) -> Response:
    _periodo_ok(de, ate)
    recebimentos = (
        db.query(Recebimento)
        .filter(Recebimento.data >= de, Recebimento.data <= ate)
        .order_by(Recebimento.data.asc(), Recebimento.id.asc())
        .all()
    )
    total_entradas = sum((_dec(r.valor) for r in recebimentos), Decimal("0"))

    bolso_q = (
        db.query(DiarioEntrada.data, DiarioTrabalho.ajudante_nome, Maquina.nome, DiarioTrabalho.valor)
        .join(DiarioTrabalho, DiarioTrabalho.entrada_id == DiarioEntrada.id)
        .join(Maquina, DiarioEntrada.maquina_id == Maquina.id)
        .filter(
            DiarioTrabalho.origem == "bolso",
            DiarioEntrada.data >= de,
            DiarioEntrada.data <= ate,
        )
        .order_by(DiarioEntrada.data.asc(), DiarioTrabalho.id.asc())
        .all()
    )
    total_bolso = sum((_dec(v) for _, _, _, v in bolso_q), Decimal("0"))

    despesas = (
        db.query(Despesa)
        .filter(Despesa.data >= de, Despesa.data <= ate)
        .order_by(Despesa.data.asc(), Despesa.id.asc())
        .all()
    )
    total_despesas = sum((_dec(d.valor) for d in despesas), Decimal("0"))
    total_saidas = total_bolso + total_despesas

    pdf = pdf_resultado(
        get_config(db), de, ate,
        recebimentos, total_entradas,
        bolso_q, total_bolso,
        despesas, total_despesas,
        total_saidas, float(total_entradas - total_saidas),
    )
    return _resp(pdf, f"resultado-{de.isoformat()}-a-{ate.isoformat()}.pdf")


# -------- 6) fechamento (registrado) e prévia --------

@router.get("/fechamento-previa")
def rel_fechamento_previa(de: date, ate: date, db: Session = Depends(get_db)) -> Response:
    _periodo_ok(de, ate)
    maquinas, servicos, adiantamentos, devido, adiantado, saldo = _calcular_previa(db, de, ate)
    label = f"{data_curta(de)} a {data_curta(ate)}"
    pdf = pdf_fechamento(
        get_config(db),
        numero="PRÉVIA",
        sub=f"Prévia . período {label}",
        maquinas=maquinas,
        servicos=servicos,
        adiantamentos=adiantamentos,
        total_devido=devido,
        total_adiantado=adiantado,
        saldo=saldo,
        obs=None,
        previa=True,
    )
    return _resp(pdf, f"fechamento-previa-{de.isoformat()}-a-{ate.isoformat()}.pdf")


@router.get("/fechamento/{fechamento_id}")
def rel_fechamento(fechamento_id: int, db: Session = Depends(get_db)) -> Response:
    fech = db.get(Fechamento, fechamento_id)
    if fech is None:
        raise HTTPException(status_code=404, detail="Fechamento não encontrado")
    maquinas = (
        db.query(Maquina)
        .filter(Maquina.fechamento_id == fech.id)
        .order_by(Maquina.data_finalizacao, Maquina.id)
        .all()
    )
    servicos = (
        db.query(Servico)
        .filter(Servico.fechamento_id == fech.id)
        .order_by(Servico.data_finalizacao, Servico.id)
        .all()
    )
    adiantamentos = (
        db.query(Recebimento)
        .filter(Recebimento.fechamento_id == fech.id, Recebimento.tipo == "adiantamento")
        .order_by(Recebimento.data.asc(), Recebimento.id.asc())
        .all()
    )
    label = f"{data_curta(fech.periodo_de)} a {data_curta(fech.periodo_ate)}"
    pdf = pdf_fechamento(
        get_config(db),
        numero=fech.numero,
        sub=f"{fech.numero} . período {label}",
        maquinas=maquinas,
        servicos=servicos,
        adiantamentos=adiantamentos,
        total_devido=_dec(fech.total_devido),
        total_adiantado=_dec(fech.total_adiantado),
        saldo=_dec(fech.saldo),
        obs=fech.obs,
    )
    return _resp(pdf, f"fechamento-{slug(fech.numero)}.pdf")
