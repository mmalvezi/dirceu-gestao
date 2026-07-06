"""Serviços avulsos — irmão de máquina (CRUD + diário). Rotas protegidas.

Trabalho pontual que não é empreita de máquina, mas que o Dirceu recebe e também
entra no fechamento. Reaproveita ao máximo os padrões das máquinas: origens,
snapshot, "eu trabalhei", custo do Dirceu = bolso + despesas vinculadas ao serviço.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case
from sqlalchemy.orm import Session, selectinload

from app.calc import (
    Agregados,
    agregados_por_servico,
    calcular_margem_pct,
    ultimos_por_servico,
)
from app.database import get_db
from app.models import Despesa, Recebimento, Servico, ServicoEntrada, ServicoTrabalho
from app.routers.diario import montar_trabalho_kwargs
from app.schemas import (
    DiarioEntradaIn,
    ExclusaoMaquinaOut,
    ServicoCreate,
    ServicoDetalheOut,
    ServicoEntradaOut,
    ServicoEntradaSalvaOut,
    ServicoOut,
    ServicoUpdate,
    TrabalhoOut,
    UltimoLancamento,
)
from app.security import get_current_user

router = APIRouter(
    prefix="/servicos",
    tags=["servicos"],
    dependencies=[Depends(get_current_user)],
)

# Ordem: aberto, depois finalizado, depois fechado.
_ORDEM_STATUS = case(
    (Servico.status == "aberto", 0),
    (Servico.status == "finalizado", 1),
    (Servico.status == "fechado", 2),
    else_=3,
)


def _get_or_404(db: Session, servico_id: int) -> Servico:
    servico = db.get(Servico, servico_id)
    if servico is None:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    return servico


def _montar_out(servico: Servico, ag: Agregados, ultimo: dict | None) -> ServicoOut:
    resultado, pct = calcular_margem_pct(servico.valor, ag.custo_dirceu)
    return ServicoOut(
        id=servico.id,
        descricao=servico.descricao,
        cliente=servico.cliente,
        valor=float(servico.valor),
        status=servico.status,
        data_inicio=servico.data_inicio,
        data_finalizacao=servico.data_finalizacao,
        obs=servico.obs,
        custo_dirceu=float(ag.custo_dirceu),
        custo_bolso_diarias=float(ag.bolso_diarias),
        custo_despesas=float(ag.despesas),
        custo_epr=float(ag.custo_epr),
        horas=float(ag.horas),
        resultado=float(resultado),
        pct_consumido=pct,
        ultimo_lancamento=UltimoLancamento(**ultimo) if ultimo else None,
    )


# ==================== CRUD ====================

@router.get("", response_model=list[ServicoOut])
def listar(
    status_: str | None = Query(None, alias="status"),
    q: str | None = None,
    db: Session = Depends(get_db),
) -> list[ServicoOut]:
    query = db.query(Servico)
    if status_:
        query = query.filter(Servico.status == status_)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Servico.descricao.ilike(like)) | (Servico.cliente.ilike(like))
        )
    servicos = query.order_by(
        _ORDEM_STATUS, Servico.data_inicio.desc(), Servico.id.desc()
    ).all()

    ids = [s.id for s in servicos]
    ags = agregados_por_servico(db, ids)
    ultimos = ultimos_por_servico(db, ids)
    return [_montar_out(s, ags.get(s.id, Agregados()), ultimos.get(s.id)) for s in servicos]


@router.get("/{servico_id}", response_model=ServicoDetalheOut)
def detalhe(servico_id: int, db: Session = Depends(get_db)) -> ServicoDetalheOut:
    servico = _get_or_404(db, servico_id)
    ags = agregados_por_servico(db, [servico.id])
    ultimos = ultimos_por_servico(db, [servico.id])
    base = _montar_out(servico, ags.get(servico.id, Agregados()), ultimos.get(servico.id))
    return ServicoDetalheOut(**base.model_dump(), diario=_listar_diario(db, servico.id))


@router.post("", response_model=ServicoOut, status_code=status.HTTP_201_CREATED)
def criar(payload: ServicoCreate, db: Session = Depends(get_db)) -> ServicoOut:
    servico = Servico(**payload.model_dump(), status="aberto")
    db.add(servico)
    db.commit()
    db.refresh(servico)
    return _montar_out(servico, Agregados(), None)


@router.put("/{servico_id}", response_model=ServicoOut)
def atualizar(
    servico_id: int, payload: ServicoUpdate, db: Session = Depends(get_db)
) -> ServicoOut:
    servico = _get_or_404(db, servico_id)
    if servico.status == "fechado":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Serviço fechado não pode ser alterado.",
        )

    data = payload.model_dump(exclude_unset=True)
    novo_status = data.get("status", servico.status)
    if novo_status == "fechado":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Status 'fechado' é definido pelo fechamento.",
        )

    for campo in ("descricao", "cliente", "valor", "data_inicio", "obs"):
        if campo in data:
            setattr(servico, campo, data[campo])

    if "status" in data and novo_status != servico.status:
        if servico.status == "aberto" and novo_status == "finalizado":
            servico.status = "finalizado"
            servico.data_finalizacao = data.get("data_finalizacao") or date.today()
        elif servico.status == "finalizado" and novo_status == "aberto":
            servico.status = "aberto"
            servico.data_finalizacao = None
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Transição de status inválida: {servico.status} -> {novo_status}",
            )
    elif "data_finalizacao" in data:
        servico.data_finalizacao = data["data_finalizacao"]

    db.commit()
    db.refresh(servico)
    ags = agregados_por_servico(db, [servico.id])
    ultimos = ultimos_por_servico(db, [servico.id])
    return _montar_out(servico, ags.get(servico.id, Agregados()), ultimos.get(servico.id))


@router.delete("/{servico_id}", response_model=ExclusaoMaquinaOut)
def excluir(servico_id: int, db: Session = Depends(get_db)) -> ExclusaoMaquinaOut:
    """Exclui serviço NÃO fechado (mesmo com lançamentos); desvincula recebimentos/despesas."""
    servico = _get_or_404(db, servico_id)
    if servico.status == "fechado":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Serviço fechado não pode ser excluído (faz parte de um fechamento).",
        )
    tem_quitado = (
        db.query(Recebimento.id)
        .filter(Recebimento.servico_id == servico_id, Recebimento.status == "quitado")
        .first()
        is not None
    )
    if tem_quitado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Serviço tem recebimento já quitado (em um fechamento); não pode ser excluído.",
        )

    diario_removido = (
        db.query(ServicoEntrada.id).filter(ServicoEntrada.servico_id == servico_id).count()
    )
    recebimentos_desvinculados = (
        db.query(Recebimento)
        .filter(Recebimento.servico_id == servico_id)
        .update({Recebimento.servico_id: None}, synchronize_session=False)
    )
    despesas_desvinculadas = (
        db.query(Despesa)
        .filter(Despesa.servico_id == servico_id)
        .update({Despesa.servico_id: None}, synchronize_session=False)
    )
    db.delete(servico)  # CASCADE remove o diário do serviço
    db.commit()
    return ExclusaoMaquinaOut(
        excluida=True,
        diario_removido=diario_removido,
        recebimentos_desvinculados=recebimentos_desvinculados,
        despesas_desvinculadas=despesas_desvinculadas,
    )


# ==================== Diário do serviço ====================

def _montar_entrada_out(entrada: ServicoEntrada) -> ServicoEntradaOut:
    trabalhos = sorted(entrada.trabalhos, key=lambda t: t.id)
    total_horas = sum((Decimal(str(t.horas)) for t in trabalhos), Decimal("0"))
    total_valor = sum((Decimal(str(t.valor)) for t in trabalhos), Decimal("0"))
    return ServicoEntradaOut(
        id=entrada.id,
        servico_id=entrada.servico_id,
        data=entrada.data,
        descricao=entrada.descricao,
        trabalhos=[
            TrabalhoOut(
                id=t.id, ajudante_id=t.ajudante_id, ajudante_nome=t.ajudante_nome,
                horas=float(t.horas), valor=float(t.valor), origem=t.origem, proprio=t.proprio,
            )
            for t in trabalhos
        ],
        total_horas=float(total_horas),
        total_valor=float(total_valor),
    )


def _listar_diario(db: Session, servico_id: int) -> list[ServicoEntradaOut]:
    entradas = (
        db.query(ServicoEntrada)
        .filter(ServicoEntrada.servico_id == servico_id)
        .options(selectinload(ServicoEntrada.trabalhos))
        .order_by(ServicoEntrada.data.desc(), ServicoEntrada.id.desc())
        .all()
    )
    return [_montar_entrada_out(e) for e in entradas]


def _get_lancavel(db: Session, servico_id: int) -> Servico:
    servico = db.get(Servico, servico_id)
    if servico is None:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    if servico.status == "fechado":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Serviço fechado não recebe lançamentos.",
        )
    return servico


def _validar_trabalhos(payload: DiarioEntradaIn, db: Session) -> list[ServicoTrabalho]:
    if not payload.descricao or not payload.descricao.strip():
        raise HTTPException(status_code=422, detail="Descrição obrigatória")
    if not payload.trabalhos:
        raise HTTPException(status_code=422, detail="Lance pelo menos um trabalho")
    return [ServicoTrabalho(**montar_trabalho_kwargs(t, db)) for t in payload.trabalhos]


def _com_aviso(entrada: ServicoEntrada, servico: Servico) -> ServicoEntradaSalvaOut:
    aviso = "Lançamento em serviço finalizado." if servico.status == "finalizado" else None
    base = _montar_entrada_out(entrada)
    return ServicoEntradaSalvaOut(**base.model_dump(), aviso=aviso)


@router.post(
    "/{servico_id}/diario",
    response_model=ServicoEntradaSalvaOut,
    status_code=status.HTTP_201_CREATED,
)
def criar_entrada(
    servico_id: int, payload: DiarioEntradaIn, db: Session = Depends(get_db)
) -> ServicoEntradaSalvaOut:
    servico = _get_lancavel(db, servico_id)
    trabalhos = _validar_trabalhos(payload, db)
    entrada = ServicoEntrada(
        servico_id=servico.id, data=payload.data, descricao=payload.descricao.strip()
    )
    entrada.trabalhos.extend(trabalhos)
    db.add(entrada)
    db.commit()
    db.refresh(entrada)
    return _com_aviso(entrada, servico)


@router.put("/{servico_id}/diario/{entrada_id}", response_model=ServicoEntradaSalvaOut)
def atualizar_entrada(
    servico_id: int, entrada_id: int, payload: DiarioEntradaIn, db: Session = Depends(get_db)
) -> ServicoEntradaSalvaOut:
    servico = _get_lancavel(db, servico_id)
    entrada = db.get(ServicoEntrada, entrada_id)
    if entrada is None or entrada.servico_id != servico_id:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    novos = _validar_trabalhos(payload, db)
    entrada.data = payload.data
    entrada.descricao = payload.descricao.strip()
    entrada.trabalhos.clear()
    db.flush()
    entrada.trabalhos.extend(novos)
    db.commit()
    db.refresh(entrada)
    return _com_aviso(entrada, servico)


@router.delete(
    "/{servico_id}/diario/{entrada_id}", status_code=status.HTTP_204_NO_CONTENT
)
def excluir_entrada(
    servico_id: int, entrada_id: int, db: Session = Depends(get_db)
) -> None:
    _get_lancavel(db, servico_id)
    entrada = db.get(ServicoEntrada, entrada_id)
    if entrada is None or entrada.servico_id != servico_id:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    db.delete(entrada)
    db.commit()
