"""Fechamento: prévia por período e registro transacional do acerto com a EPR.

Conceito (seção 1 do plano): escolhe-se um período De/Até. Entram as MÁQUINAS
FINALIZADAS no período (empreita integral) e, a abater, os ADIANTAMENTOS EM ABERTO
vinculados a essas máquinas OU sem vínculo. SALDO = devido − adiantado.

Registrar o acerto efetiva tudo numa transação única: máquinas → "fechada",
adiantamentos → "quitado", nasce um Recebimento tipo "fechamento" (se saldo > 0),
e o fechamento ganha número FEC-XXXX.

NÃO existe "desfazer fechamento" nesta versão (decisão de escopo): um acerto
registrado é histórico imutável. Correções são combinadas manualmente e lançadas
como novo adiantamento/obs, nunca revertendo o fechamento.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Fechamento, Maquina, Recebimento, Servico
from app.routers.config import get_config
from app.schemas import (
    FechamentoCreate,
    FechamentoDetalheOut,
    FechamentoOut,
    FechamentoPrevia,
)
from app.security import get_current_user

router = APIRouter(
    prefix="/fechamentos",
    tags=["fechamento"],
    dependencies=[Depends(get_current_user)],
)


def _validar_periodo(de: date, ate: date) -> None:
    if de > ate:
        raise HTTPException(
            status_code=422, detail="Período inválido: 'de' deve ser <= 'ate'."
        )


def _calcular_previa(
    db: Session, de: date, ate: date
) -> tuple[list[Maquina], list[Servico], list[Recebimento], Decimal, Decimal, Decimal]:
    """Núcleo compartilhado entre a prévia e o registro (nunca confiar no cliente).

    Entram máquinas FINALIZADAS (empreita) e serviços FINALIZADOS (valor) no período.
    """
    maquinas = (
        db.query(Maquina)
        .filter(
            Maquina.status == "finalizada",
            Maquina.data_finalizacao >= de,
            Maquina.data_finalizacao <= ate,
        )
        .order_by(Maquina.data_finalizacao, Maquina.id)
        .all()
    )
    servicos = (
        db.query(Servico)
        .filter(
            Servico.status == "finalizado",
            Servico.data_finalizacao >= de,
            Servico.data_finalizacao <= ate,
        )
        .order_by(Servico.data_finalizacao, Servico.id)
        .all()
    )

    if not maquinas and not servicos:
        # Nada no período: prévia vazia (não abate adiantamentos flutuantes).
        return [], [], [], Decimal("0"), Decimal("0"), Decimal("0")

    mids = [m.id for m in maquinas]
    sids = [s.id for s in servicos]
    adiantamentos = (
        db.query(Recebimento)
        .filter(
            Recebimento.tipo == "adiantamento",
            Recebimento.status == "aberto",
            or_(
                Recebimento.maquina_id.in_(mids),
                Recebimento.servico_id.in_(sids),
                # flutuante: sem vínculo com máquina nem serviço
                (Recebimento.maquina_id.is_(None) & Recebimento.servico_id.is_(None)),
            ),
        )
        .order_by(Recebimento.data.desc(), Recebimento.id.desc())
        .all()
    )

    total_devido = sum(
        (Decimal(str(m.empreita)) for m in maquinas), Decimal("0")
    ) + sum((Decimal(str(s.valor)) for s in servicos), Decimal("0"))
    total_adiantado = sum((Decimal(str(a.valor)) for a in adiantamentos), Decimal("0"))
    saldo = total_devido - total_adiantado
    return maquinas, servicos, adiantamentos, total_devido, total_adiantado, saldo


def _detalhe_out(db: Session, fechamento: Fechamento) -> FechamentoDetalheOut:
    maquinas = (
        db.query(Maquina).filter(Maquina.fechamento_id == fechamento.id).all()
    )
    servicos = (
        db.query(Servico).filter(Servico.fechamento_id == fechamento.id).all()
    )
    adiantamentos = (
        db.query(Recebimento)
        .filter(
            Recebimento.fechamento_id == fechamento.id,
            Recebimento.tipo == "adiantamento",
        )
        .order_by(Recebimento.data.desc(), Recebimento.id.desc())
        .all()
    )
    receb_fech = (
        db.query(Recebimento)
        .filter(
            Recebimento.fechamento_id == fechamento.id,
            Recebimento.tipo == "fechamento",
        )
        .first()
    )
    return FechamentoDetalheOut(
        id=fechamento.id,
        numero=fechamento.numero,
        data_geracao=fechamento.data_geracao,
        periodo_de=fechamento.periodo_de,
        periodo_ate=fechamento.periodo_ate,
        total_devido=float(fechamento.total_devido),
        total_adiantado=float(fechamento.total_adiantado),
        saldo=float(fechamento.saldo),
        obs=fechamento.obs,
        maquinas=maquinas,
        servicos=servicos,
        adiantamentos=adiantamentos,
        recebimento_fechamento=receb_fech,
    )


@router.get("/previa", response_model=FechamentoPrevia)
def previa(de: date, ate: date, db: Session = Depends(get_db)) -> FechamentoPrevia:
    _validar_periodo(de, ate)
    maquinas, servicos, adiantamentos, devido, adiantado, saldo = _calcular_previa(db, de, ate)
    return FechamentoPrevia(
        periodo_de=de,
        periodo_ate=ate,
        maquinas=maquinas,
        servicos=servicos,
        adiantamentos=adiantamentos,
        total_devido=float(devido),
        total_adiantado=float(adiantado),
        saldo=float(saldo),
        pode_registrar=len(maquinas) + len(servicos) >= 1,
    )


@router.post("", response_model=FechamentoDetalheOut, status_code=status.HTTP_201_CREATED)
def registrar(
    payload: FechamentoCreate, db: Session = Depends(get_db)
) -> FechamentoDetalheOut:
    de, ate = payload.periodo_de, payload.periodo_ate
    _validar_periodo(de, ate)

    # Recalcula SEMPRE no servidor — nunca confiar em números vindos do cliente.
    maquinas, servicos, adiantamentos, devido, adiantado, saldo = _calcular_previa(db, de, ate)
    if not maquinas and not servicos:
        raise HTTPException(
            status_code=422,
            detail="Não há máquinas nem serviços finalizados no período.",
        )

    # ---- Transação única ----
    config = get_config(db)
    numero = f"FEC-{config.prox_fec:04d}"

    fechamento = Fechamento(
        numero=numero,
        periodo_de=de,
        periodo_ate=ate,
        total_devido=devido,
        total_adiantado=adiantado,
        saldo=saldo,
        obs=payload.obs,
    )
    db.add(fechamento)
    db.flush()  # garante fechamento.id para os vínculos

    for m in maquinas:
        m.status = "fechada"
        m.fechamento_id = fechamento.id
    for s in servicos:
        s.status = "fechado"
        s.fechamento_id = fechamento.id
    for a in adiantamentos:
        a.status = "quitado"
        a.fechamento_id = fechamento.id

    # Só nasce recebimento se ENTROU dinheiro novo (saldo > 0).
    if saldo > 0:
        db.add(
            Recebimento(
                tipo="fechamento",
                data=date.today(),
                valor=saldo,
                status="quitado",
                fechamento_id=fechamento.id,
                obs=f"Acerto {numero}",
            )
        )

    config.prox_fec += 1
    db.commit()
    db.refresh(fechamento)
    return _detalhe_out(db, fechamento)


@router.get("", response_model=list[FechamentoOut])
def listar(db: Session = Depends(get_db)) -> list[FechamentoOut]:
    fechamentos = (
        db.query(Fechamento).order_by(Fechamento.data_geracao.desc(), Fechamento.id.desc()).all()
    )
    saida = []
    for f in fechamentos:
        maquinas = db.query(Maquina).filter(Maquina.fechamento_id == f.id).all()
        servicos = db.query(Servico).filter(Servico.fechamento_id == f.id).all()
        saida.append(
            FechamentoOut(
                id=f.id,
                numero=f.numero,
                data_geracao=f.data_geracao,
                periodo_de=f.periodo_de,
                periodo_ate=f.periodo_ate,
                total_devido=float(f.total_devido),
                total_adiantado=float(f.total_adiantado),
                saldo=float(f.saldo),
                obs=f.obs,
                maquinas=maquinas,
                servicos=servicos,
            )
        )
    return saida


@router.get("/{fechamento_id}", response_model=FechamentoDetalheOut)
def detalhe(fechamento_id: int, db: Session = Depends(get_db)) -> FechamentoDetalheOut:
    fechamento = db.get(Fechamento, fechamento_id)
    if fechamento is None:
        raise HTTPException(status_code=404, detail="Fechamento não encontrado")
    return _detalhe_out(db, fechamento)
