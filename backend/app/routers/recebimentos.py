"""Recebimentos do Dirceu: adiantamentos (criáveis) e fechamentos (só via Fase 8)."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Maquina, Recebimento
from app.schemas import RecebimentoCreate, RecebimentoOut, RecebimentoUpdate
from app.security import get_current_user

router = APIRouter(
    prefix="/recebimentos",
    tags=["financeiro"],
    dependencies=[Depends(get_current_user)],
)


def _get_or_404(db: Session, receb_id: int) -> Recebimento:
    receb = db.get(Recebimento, receb_id)
    if receb is None:
        raise HTTPException(status_code=404, detail="Recebimento não encontrado")
    return receb


def _exigir_editavel(receb: Recebimento) -> None:
    """Só adiantamento 'aberto' pode ser alterado/excluído."""
    if receb.tipo != "adiantamento" or receb.status != "aberto":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Recebimento quitado/de fechamento não pode ser alterado.",
        )


def _snapshot_maquina(db: Session, maquina_id: int) -> str:
    maquina = db.get(Maquina, maquina_id)
    if maquina is None:
        raise HTTPException(status_code=404, detail="Máquina não encontrada")
    return maquina.nome


@router.get("", response_model=list[RecebimentoOut])
def listar(
    tipo: str | None = None,
    status_: str | None = Query(None, alias="status"),
    de: date | None = None,
    ate: date | None = None,
    maquina_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[Recebimento]:
    query = db.query(Recebimento)
    if tipo:
        query = query.filter(Recebimento.tipo == tipo)
    if status_:
        query = query.filter(Recebimento.status == status_)
    if de:
        query = query.filter(Recebimento.data >= de)
    if ate:
        query = query.filter(Recebimento.data <= ate)
    if maquina_id is not None:
        query = query.filter(Recebimento.maquina_id == maquina_id)
    return query.order_by(Recebimento.data.desc(), Recebimento.id.desc()).all()


@router.post("", response_model=RecebimentoOut, status_code=status.HTTP_201_CREATED)
def criar(payload: RecebimentoCreate, db: Session = Depends(get_db)) -> Recebimento:
    if payload.tipo != "adiantamento":
        raise HTTPException(
            status_code=422,
            detail="Recebimentos de fechamento são criados pelo próprio fechamento.",
        )
    if payload.valor <= 0:
        raise HTTPException(status_code=422, detail="Valor deve ser maior que zero")

    maquina_nome = None
    if payload.maquina_id is not None:
        maquina_nome = _snapshot_maquina(db, payload.maquina_id)

    receb = Recebimento(
        tipo="adiantamento",
        data=payload.data,
        valor=payload.valor,
        maquina_id=payload.maquina_id,
        maquina_nome=maquina_nome,
        status="aberto",
        obs=payload.obs,
    )
    db.add(receb)
    db.commit()
    db.refresh(receb)
    return receb


@router.put("/{receb_id}", response_model=RecebimentoOut)
def atualizar(
    receb_id: int, payload: RecebimentoUpdate, db: Session = Depends(get_db)
) -> Recebimento:
    receb = _get_or_404(db, receb_id)
    _exigir_editavel(receb)

    data = payload.model_dump(exclude_unset=True)
    if "valor" in data:
        if data["valor"] is None or data["valor"] <= 0:
            raise HTTPException(status_code=422, detail="Valor deve ser maior que zero")
        receb.valor = data["valor"]
    if "data" in data and data["data"] is not None:
        receb.data = data["data"]
    if "obs" in data:
        receb.obs = data["obs"]
    if "maquina_id" in data:
        if data["maquina_id"] is None:
            receb.maquina_id = None
            receb.maquina_nome = None
        else:
            receb.maquina_nome = _snapshot_maquina(db, data["maquina_id"])
            receb.maquina_id = data["maquina_id"]

    db.commit()
    db.refresh(receb)
    return receb


@router.delete("/{receb_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(receb_id: int, db: Session = Depends(get_db)) -> None:
    receb = _get_or_404(db, receb_id)
    _exigir_editavel(receb)
    db.delete(receb)
    db.commit()
