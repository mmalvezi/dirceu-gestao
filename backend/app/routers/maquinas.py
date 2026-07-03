"""CRUD de máquinas com regras de status e agregados calculados (rotas protegidas)."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, or_
from sqlalchemy.orm import Session

from app.calc import Agregados, agregados_por_maquina, calcular_margem_pct, ultimos_por_maquina
from app.database import get_db
from app.models import DiarioEntrada, Maquina, Recebimento
from app.routers.diario import listar_diario
from app.schemas import (
    MaquinaCreate,
    MaquinaDetalheOut,
    MaquinaOut,
    MaquinaUpdate,
    UltimoLancamento,
)
from app.security import get_current_user

router = APIRouter(
    prefix="/maquinas",
    tags=["maquinas"],
    dependencies=[Depends(get_current_user)],
)

# Ordem de exibição por status: andamento, depois finalizada, depois fechada.
_ORDEM_STATUS = case(
    (Maquina.status == "andamento", 0),
    (Maquina.status == "finalizada", 1),
    (Maquina.status == "fechada", 2),
    else_=3,
)


def _get_or_404(db: Session, maquina_id: int) -> Maquina:
    maquina = db.get(Maquina, maquina_id)
    if maquina is None:
        raise HTTPException(status_code=404, detail="Máquina não encontrada")
    return maquina


def _montar_out(maquina: Maquina, ag: Agregados, ultimo: dict | None) -> MaquinaOut:
    # Margem/pct pela contabilidade do DIRCEU: só bolso + despesas.
    margem, pct = calcular_margem_pct(maquina.empreita, ag.custo_dirceu)
    return MaquinaOut(
        id=maquina.id,
        nome=maquina.nome,
        cliente=maquina.cliente,
        empreita=float(maquina.empreita),
        status=maquina.status,
        data_inicio=maquina.data_inicio,
        data_finalizacao=maquina.data_finalizacao,
        obs=maquina.obs,
        custo_dirceu=float(ag.custo_dirceu),
        custo_bolso_diarias=float(ag.bolso_diarias),
        custo_despesas=float(ag.despesas),
        custo_epr=float(ag.custo_epr),
        horas=float(ag.horas),
        margem=float(margem),
        pct_consumido=pct,
        ultimo_lancamento=UltimoLancamento(**ultimo) if ultimo else None,
    )


@router.get("", response_model=list[MaquinaOut])
def listar(
    status_: str | None = Query(None, alias="status"),
    q: str | None = None,
    db: Session = Depends(get_db),
) -> list[MaquinaOut]:
    query = db.query(Maquina)
    if status_:
        query = query.filter(Maquina.status == status_)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Maquina.nome.ilike(like), Maquina.cliente.ilike(like)))
    maquinas = query.order_by(
        _ORDEM_STATUS, Maquina.data_inicio.desc(), Maquina.id.desc()
    ).all()

    ids = [m.id for m in maquinas]
    agregados = agregados_por_maquina(db, ids)
    ultimos = ultimos_por_maquina(db, ids)
    return [
        _montar_out(m, agregados.get(m.id, Agregados()), ultimos.get(m.id))
        for m in maquinas
    ]


@router.get("/{maquina_id}", response_model=MaquinaDetalheOut)
def detalhe(maquina_id: int, db: Session = Depends(get_db)) -> MaquinaDetalheOut:
    maquina = _get_or_404(db, maquina_id)
    agregados = agregados_por_maquina(db, [maquina.id])
    ultimos = ultimos_por_maquina(db, [maquina.id])
    base = _montar_out(maquina, agregados.get(maquina.id, Agregados()), ultimos.get(maquina.id))
    diario = listar_diario(db, maquina.id)
    return MaquinaDetalheOut(**base.model_dump(), diario=diario)


@router.post("", response_model=MaquinaOut, status_code=status.HTTP_201_CREATED)
def criar(payload: MaquinaCreate, db: Session = Depends(get_db)) -> MaquinaOut:
    maquina = Maquina(**payload.model_dump(), status="andamento")
    db.add(maquina)
    db.commit()
    db.refresh(maquina)
    return _montar_out(maquina, Agregados(), None)


@router.put("/{maquina_id}", response_model=MaquinaOut)
def atualizar(
    maquina_id: int, payload: MaquinaUpdate, db: Session = Depends(get_db)
) -> MaquinaOut:
    maquina = _get_or_404(db, maquina_id)

    if maquina.status == "fechada":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Máquina fechada não pode ser alterada.",
        )

    data = payload.model_dump(exclude_unset=True)
    novo_status = data.get("status", maquina.status)

    if novo_status == "fechada":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Status 'fechada' é definido pelo fechamento.",
        )

    # Campos simples (não mexem em status/data_finalizacao).
    for campo in ("nome", "cliente", "empreita", "data_inicio", "obs"):
        if campo in data:
            setattr(maquina, campo, data[campo])

    if "status" in data and novo_status != maquina.status:
        if maquina.status == "andamento" and novo_status == "finalizada":
            maquina.status = "finalizada"
            maquina.data_finalizacao = data.get("data_finalizacao") or date.today()
        elif maquina.status == "finalizada" and novo_status == "andamento":
            maquina.status = "andamento"
            maquina.data_finalizacao = None  # reabrir limpa a data
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Transição de status inválida: {maquina.status} -> {novo_status}",
            )
    elif "data_finalizacao" in data:
        # Ajuste da data sem mudar de status (ex.: corrigir a data de finalização).
        maquina.data_finalizacao = data["data_finalizacao"]

    db.commit()
    db.refresh(maquina)

    agregados = agregados_por_maquina(db, [maquina.id])
    ultimos = ultimos_por_maquina(db, [maquina.id])
    return _montar_out(maquina, agregados.get(maquina.id, Agregados()), ultimos.get(maquina.id))


@router.delete("/{maquina_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(maquina_id: int, db: Session = Depends(get_db)) -> None:
    maquina = _get_or_404(db, maquina_id)
    if maquina.status == "fechada":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Máquina fechada não pode ser alterada.",
        )
    tem_diario = (
        db.query(DiarioEntrada.id)
        .filter(DiarioEntrada.maquina_id == maquina_id)
        .first()
        is not None
    )
    tem_recebimentos = (
        db.query(Recebimento.id)
        .filter(Recebimento.maquina_id == maquina_id)
        .first()
        is not None
    )
    if tem_diario or tem_recebimentos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Máquina possui lançamentos; não pode ser excluída.",
        )
    db.delete(maquina)
    db.commit()
