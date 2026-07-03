"""Dashboard (tela Início do protótipo): KPIs, horas por dia, margens, avisos e
resumo WhatsApp. Tudo calculado por queries agregadas; datas comparadas como date.
"""

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.calc import agregados_por_maquina, calcular_margem_pct
from app.database import get_db
from app.models import DiarioEntrada, DiarioTrabalho, Maquina, Recebimento, RepasseEntrada
from app.schemas import (
    AdiantadoAbertoKpi,
    AReceberKpi,
    AReceberMaquina,
    Aviso,
    DashboardKpis,
    DashboardOut,
    DashboardPeriodo,
    HorasDia,
    MaquinaAndamentoDash,
    PagoAjudantes,
)
from app.security import get_current_user
from app.utils import data_br, data_curta, horas_fmt, moeda

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_current_user)],
)

DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def _dec(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


def _semana_corrente() -> tuple[date, date]:
    """Segunda a domingo da semana de hoje."""
    hoje = date.today()
    segunda = hoje - timedelta(days=hoje.weekday())
    return segunda, segunda + timedelta(days=6)


@router.get("", response_model=DashboardOut)
def dashboard(
    de: date | None = None,
    ate: date | None = None,
    db: Session = Depends(get_db),
) -> DashboardOut:
    hoje = date.today()
    if de is None or ate is None:
        d0, a0 = _semana_corrente()
        de = de or d0
        ate = ate or a0

    # ---------- KPIs do período (diário) ----------
    # Valores por origem + horas, filtrando pela data da ENTRADA.
    rows = (
        db.query(
            DiarioTrabalho.origem,
            func.coalesce(func.sum(DiarioTrabalho.valor), 0),
            func.coalesce(func.sum(DiarioTrabalho.horas), 0),
        )
        .join(DiarioEntrada, DiarioTrabalho.entrada_id == DiarioEntrada.id)
        .filter(DiarioEntrada.data >= de, DiarioEntrada.data <= ate)
        .group_by(DiarioTrabalho.origem)
        .all()
    )
    valor_origem = {o: _dec(v) for o, v, _ in rows}
    horas_periodo = sum((_dec(h) for _, _, h in rows), Decimal("0"))
    pago_repasse = valor_origem.get("repasse", Decimal("0"))
    pago_bolso = valor_origem.get("bolso", Decimal("0"))
    pago_epr = valor_origem.get("epr_direto", Decimal("0"))
    pago_total = pago_repasse + pago_bolso + pago_epr

    ajudantes_ativos = (
        db.query(func.count(func.distinct(DiarioTrabalho.ajudante_nome)))
        .join(DiarioEntrada, DiarioTrabalho.entrada_id == DiarioEntrada.id)
        .filter(DiarioEntrada.data >= de, DiarioEntrada.data <= ate)
        .scalar()
        or 0
    )

    # ---------- Posições atuais (sem período) ----------
    adiantado_total, adiantado_qtd = (
        db.query(
            func.coalesce(func.sum(Recebimento.valor), 0), func.count(Recebimento.id)
        )
        .filter(Recebimento.tipo == "adiantamento", Recebimento.status == "aberto")
        .one()
    )
    adiantado_total = _dec(adiantado_total)

    # A receber: máquinas finalizadas, empreita − adiantamentos ABERTOS vinculados.
    finalizadas = db.query(Maquina).filter(Maquina.status == "finalizada").all()
    a_receber_lista: list[AReceberMaquina] = []
    a_receber_total = Decimal("0")
    abertos_por_maquina: dict[int, Decimal] = {}
    if finalizadas:
        rows = (
            db.query(
                Recebimento.maquina_id,
                func.coalesce(func.sum(Recebimento.valor), 0),
            )
            .filter(
                Recebimento.tipo == "adiantamento",
                Recebimento.status == "aberto",
                Recebimento.maquina_id.in_([m.id for m in finalizadas]),
            )
            .group_by(Recebimento.maquina_id)
            .all()
        )
        abertos_por_maquina = {mid: _dec(v) for mid, v in rows}
        for m in finalizadas:
            valor = _dec(m.empreita) - abertos_por_maquina.get(m.id, Decimal("0"))
            a_receber_lista.append(AReceberMaquina(nome=m.nome, valor=float(valor)))
            a_receber_total += valor

    # ---------- Horas por dia (dias sem lançamento = 0) ----------
    rows = (
        db.query(
            DiarioEntrada.data,
            func.coalesce(func.sum(DiarioTrabalho.horas), 0),
        )
        .join(DiarioTrabalho, DiarioTrabalho.entrada_id == DiarioEntrada.id)
        .filter(DiarioEntrada.data >= de, DiarioEntrada.data <= ate)
        .group_by(DiarioEntrada.data)
        .all()
    )
    horas_por_data = {d: _dec(h) for d, h in rows}
    horas_por_dia: list[HorasDia] = []
    d = de
    while d <= ate:
        horas_por_dia.append(
            HorasDia(
                dia=DIAS_SEMANA[d.weekday()],
                data=d,
                horas=float(horas_por_data.get(d, Decimal("0"))),
                hoje=(d == hoje),
            )
        )
        d += timedelta(days=1)

    # ---------- Máquinas não-fechadas com custo/margem ----------
    nao_fechadas = (
        db.query(Maquina).filter(Maquina.status.in_(["andamento", "finalizada"])).all()
    )
    agregados = agregados_por_maquina(db, [m.id for m in nao_fechadas])
    maquinas_dash: list[MaquinaAndamentoDash] = []
    for m in nao_fechadas:
        custo, _h = agregados.get(m.id, (Decimal("0"), Decimal("0")))
        margem, pct = calcular_margem_pct(m.empreita, custo)
        maquinas_dash.append(
            MaquinaAndamentoDash(
                id=m.id,
                nome=m.nome,
                status=m.status,
                empreita=float(m.empreita),
                custo=float(custo),
                margem=float(margem),
                pct_consumido=pct,
            )
        )
    maquinas_dash.sort(key=lambda x: x.pct_consumido, reverse=True)

    # ---------- Avisos (por regra; sem condição -> lista vazia) ----------
    avisos: list[Aviso] = []

    # warn: finalizada há mais de 7 dias sem fechamento (+ adiantamento a abater).
    for m in finalizadas:
        if m.data_finalizacao is None:
            continue
        dias = (hoje - m.data_finalizacao).days
        if dias > 7:
            texto = f"{m.nome} está finalizada há {dias} dias sem fechamento."
            aberto = abertos_por_maquina.get(m.id, Decimal("0"))
            if aberto > 0:
                texto += (
                    f" Há R$ {moeda(aberto)} adiantados a abater —"
                    " que tal agendar o acerto?"
                )
            avisos.append(
                Aviso(nivel="warn", texto=texto, tipo="fechamento_pendente", maquina_id=m.id)
            )

    # hot: andamento com custo >= 60% da empreita (>= 70% = alerta forte).
    for mq in maquinas_dash:
        if mq.status == "andamento" and mq.pct_consumido >= 60:
            if mq.pct_consumido >= 70:
                texto = (
                    f"{mq.nome}: o custo já consumiu {mq.pct_consumido}% da empreita"
                    f" (R$ {moeda(mq.custo)} de R$ {moeda(mq.empreita)})."
                    " Margem em risco — reveja o combinado!"
                )
            else:
                texto = (
                    f"{mq.nome}: o custo chegou a {mq.pct_consumido}% da empreita"
                    f" (R$ {moeda(mq.custo)} de R$ {moeda(mq.empreita)})"
                    " e ela ainda está em andamento. Fica de olho na margem."
                )
            avisos.append(
                Aviso(nivel="hot", texto=texto, tipo="custo_alto", maquina_id=mq.id)
            )

    # caixa de repasse (acumulado): sobra -> info; negativo -> hot.
    repasse_recebido_total = _dec(
        db.query(func.coalesce(func.sum(RepasseEntrada.valor), 0)).scalar()
    )
    repasse_pago_total = _dec(
        db.query(func.coalesce(func.sum(DiarioTrabalho.valor), 0))
        .filter(DiarioTrabalho.origem == "repasse")
        .scalar()
    )
    caixa = repasse_recebido_total - repasse_pago_total
    if caixa > 0:
        avisos.append(
            Aviso(
                nivel="info",
                tipo="caixa",
                texto=(
                    f"Repasses da EPR: recebeu R$ {moeda(repasse_recebido_total)}"
                    f" pra repassar e repassou R$ {moeda(repasse_pago_total)} —"
                    f" sobram R$ {moeda(caixa)} em caixa de repasse."
                ),
            )
        )
    elif caixa < 0:
        avisos.append(
            Aviso(
                nivel="hot",
                tipo="caixa",
                texto=(
                    "Repasses da EPR: você repassou MAIS do que recebeu —"
                    f" está R$ {moeda(abs(caixa))} no vermelho do próprio bolso."
                ),
            )
        )

    # warn: adiantamento aberto há mais de 30 dias.
    antigos = (
        db.query(Recebimento)
        .filter(
            Recebimento.tipo == "adiantamento",
            Recebimento.status == "aberto",
            Recebimento.data < hoje - timedelta(days=30),
        )
        .order_by(Recebimento.data)
        .all()
    )
    for a in antigos:
        dias = (hoje - a.data).days
        avisos.append(
            Aviso(
                nivel="warn",
                tipo="adiantamento_antigo",
                texto=(
                    f"Adiantamento de R$ {moeda(a.valor)} está em aberto"
                    f" desde {data_br(a.data)} (há {dias} dias)."
                ),
            )
        )

    # ---------- Resumo WhatsApp ----------
    label = f"{data_curta(de)} a {data_curta(ate)}"
    linhas = [f"*Resumo semana {label} — Dirceu*"]

    andamento = [m for m in maquinas_dash if m.status == "andamento"]
    if andamento:
        linhas.append(
            "Máquinas em andamento: "
            + ", ".join(f"{m.nome} ({m.pct_consumido}%)" for m in andamento)
        )
    if finalizadas:
        linhas.append(
            "Finalizada aguardando fechamento: "
            + ", ".join(m.nome for m in finalizadas)
        )
    linhas.append(f"Horas da equipe: {horas_fmt(horas_periodo)}h")
    pago_linha = (
        f"Pago a ajudantes: R$ {moeda(pago_total)}"
        f" (R$ {moeda(pago_repasse)} repasse EPR / R$ {moeda(pago_bolso)} do bolso"
    )
    if pago_epr > 0:
        pago_linha += f" / R$ {moeda(pago_epr)} EPR direto"
    pago_linha += ")"
    linhas.append(pago_linha)
    if adiantado_total > 0:
        linhas.append(f"Adiantado em aberto: R$ {moeda(adiantado_total)}")
    if finalizadas:
        linhas.append(f"A receber no fechamento: R$ {moeda(a_receber_total)}")

    return DashboardOut(
        periodo=DashboardPeriodo(de=de, ate=ate, label=label),
        kpis=DashboardKpis(
            horas_periodo=float(horas_periodo),
            ajudantes_ativos_periodo=ajudantes_ativos,
            pago_ajudantes=PagoAjudantes(
                total=float(pago_total),
                repasse=float(pago_repasse),
                bolso=float(pago_bolso),
                epr_direto=float(pago_epr),
            ),
            adiantado_aberto=AdiantadoAbertoKpi(
                total=float(adiantado_total), quantidade=adiantado_qtd
            ),
            a_receber=AReceberKpi(
                total=float(a_receber_total), maquinas=a_receber_lista
            ),
        ),
        horas_por_dia=horas_por_dia,
        maquinas_andamento=maquinas_dash,
        avisos=avisos,
        resumo_whatsapp="\n".join(linhas),
    )
