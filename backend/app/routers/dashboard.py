"""Dashboard (tela Início do protótipo): KPIs, horas por dia, margens, avisos e
resumo WhatsApp. Tudo calculado por queries agregadas; datas comparadas como date.
"""

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import false, func
from sqlalchemy.orm import Session

from app.calc import (
    Agregados,
    agregados_por_maquina,
    agregados_por_servico,
    ajudantes_distintos_periodo,
    calcular_margem_pct,
    horas_por_data_periodo,
    repasse_pago_total,
    trabalhos_por_origem_periodo,
)
from app.database import get_db
from app.models import Maquina, Recebimento, RepasseEntrada, Servico
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

    # ---------- KPIs do período (diário: máquinas + serviços) ----------
    por_origem = trabalhos_por_origem_periodo(db, de, ate)
    horas_periodo = sum((h for _, h in por_origem.values()), Decimal("0"))
    pago_repasse = por_origem.get("repasse", (Decimal("0"),))[0]
    pago_bolso = por_origem.get("bolso", (Decimal("0"),))[0]
    pago_epr = por_origem.get("epr_direto", (Decimal("0"),))[0]
    pago_total = pago_repasse + pago_bolso + pago_epr
    ajudantes_ativos = ajudantes_distintos_periodo(db, de, ate)

    # ---------- Posições atuais (sem período) ----------
    adiantado_total, adiantado_qtd = (
        db.query(
            func.coalesce(func.sum(Recebimento.valor), 0), func.count(Recebimento.id)
        )
        .filter(Recebimento.tipo == "adiantamento", Recebimento.status == "aberto")
        .one()
    )
    adiantado_total = _dec(adiantado_total)

    # A receber: máquinas E serviços finalizados, valor − adiantamentos ABERTOS vinculados.
    finalizadas = db.query(Maquina).filter(Maquina.status == "finalizada").all()
    finalizados = db.query(Servico).filter(Servico.status == "finalizado").all()
    a_receber_lista: list[AReceberMaquina] = []
    a_receber_total = Decimal("0")
    abertos_por_maquina: dict[int, Decimal] = {}
    abertos_por_servico: dict[int, Decimal] = {}
    if finalizadas:
        rows = (
            db.query(Recebimento.maquina_id, func.coalesce(func.sum(Recebimento.valor), 0))
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
    if finalizados:
        rows = (
            db.query(Recebimento.servico_id, func.coalesce(func.sum(Recebimento.valor), 0))
            .filter(
                Recebimento.tipo == "adiantamento",
                Recebimento.status == "aberto",
                Recebimento.servico_id.in_([s.id for s in finalizados]),
            )
            .group_by(Recebimento.servico_id)
            .all()
        )
        abertos_por_servico = {sid: _dec(v) for sid, v in rows}
        for s in finalizados:
            valor = _dec(s.valor) - abertos_por_servico.get(s.id, Decimal("0"))
            a_receber_lista.append(AReceberMaquina(nome=s.descricao, valor=float(valor)))
            a_receber_total += valor

    # ---------- Horas por dia (dias sem lançamento = 0; máquinas + serviços) ----------
    horas_por_data = horas_por_data_periodo(db, de, ate)
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

    # ---------- Trabalhos não-fechados com custo/margem (máquinas + serviços) ----------
    nao_fechadas = (
        db.query(Maquina).filter(Maquina.status.in_(["andamento", "finalizada"])).all()
    )
    ags_m = agregados_por_maquina(db, [m.id for m in nao_fechadas])
    maquinas_dash: list[MaquinaAndamentoDash] = []
    for m in nao_fechadas:
        ag = ags_m.get(m.id, Agregados())
        margem, pct = calcular_margem_pct(m.empreita, ag.custo_dirceu)
        maquinas_dash.append(
            MaquinaAndamentoDash(
                id=m.id, nome=m.nome, status=m.status, empreita=float(m.empreita),
                custo_dirceu=float(ag.custo_dirceu), margem=float(margem),
                pct_consumido=pct, tipo="maquina",
            )
        )
    servicos_abertos = (
        db.query(Servico).filter(Servico.status.in_(["aberto", "finalizado"])).all()
    )
    ags_s = agregados_por_servico(db, [s.id for s in servicos_abertos])
    for s in servicos_abertos:
        ag = ags_s.get(s.id, Agregados())
        resultado, pct = calcular_margem_pct(s.valor, ag.custo_dirceu)
        maquinas_dash.append(
            MaquinaAndamentoDash(
                id=s.id, nome=s.descricao,
                status="andamento" if s.status == "aberto" else "finalizada",
                empreita=float(s.valor), custo_dirceu=float(ag.custo_dirceu),
                margem=float(resultado), pct_consumido=pct, tipo="servico",
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

    # warn: serviço finalizado há mais de 7 dias sem fechamento.
    for s in finalizados:
        if s.data_finalizacao is None:
            continue
        dias = (hoje - s.data_finalizacao).days
        if dias > 7:
            texto = f"O serviço \"{s.descricao}\" está finalizado há {dias} dias sem fechamento."
            aberto = abertos_por_servico.get(s.id, Decimal("0"))
            if aberto > 0:
                texto += (
                    f" Há R$ {moeda(aberto)} adiantados a abater —"
                    " que tal agendar o acerto?"
                )
            avisos.append(
                Aviso(nivel="warn", texto=texto, tipo="fechamento_pendente", servico_id=s.id)
            )

    # hot: MÁQUINA em andamento com custo >= 60% da empreita (>= 70% = alerta forte).
    for mq in maquinas_dash:
        if mq.tipo == "maquina" and mq.status == "andamento" and mq.pct_consumido >= 60:
            if mq.pct_consumido >= 70:
                texto = (
                    f"{mq.nome}: seu custo já consumiu {mq.pct_consumido}% da empreita"
                    f" (R$ {moeda(mq.custo_dirceu)} de R$ {moeda(mq.empreita)})."
                    " Margem em risco — reveja o combinado!"
                )
            else:
                texto = (
                    f"{mq.nome}: seu custo chegou a {mq.pct_consumido}% da empreita"
                    f" (R$ {moeda(mq.custo_dirceu)} de R$ {moeda(mq.empreita)})"
                    " e ela ainda está em andamento. Fica de olho na margem."
                )
            avisos.append(
                Aviso(nivel="hot", texto=texto, tipo="custo_alto", maquina_id=mq.id)
            )

    # caixa de repasse (acumulado): sobra -> info; negativo -> hot.
    repasse_recebido_tot = _dec(
        db.query(func.coalesce(func.sum(RepasseEntrada.valor), 0)).scalar()
    )
    repasse_pago_tot = repasse_pago_total(db)  # dois diários
    caixa = repasse_recebido_tot - repasse_pago_tot
    if caixa > 0:
        avisos.append(
            Aviso(
                nivel="info",
                tipo="caixa",
                texto=(
                    f"Repasses da EPR: recebeu R$ {moeda(repasse_recebido_tot)}"
                    f" pra repassar e repassou R$ {moeda(repasse_pago_tot)} —"
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

    andamento = [m for m in maquinas_dash if m.tipo == "maquina" and m.status == "andamento"]
    if andamento:
        linhas.append(
            "Máquinas em andamento: "
            + ", ".join(f"{m.nome} ({m.pct_consumido}%)" for m in andamento)
        )
    servicos_and = [s.descricao for s in servicos_abertos if s.status == "aberto"]
    if servicos_and:
        linhas.append("Serviços em andamento: " + ", ".join(servicos_and))
    aguardando = [m.nome for m in finalizadas] + [s.descricao for s in finalizados]
    if aguardando:
        linhas.append("Aguardando fechamento: " + ", ".join(aguardando))
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
    if finalizadas or finalizados:
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
