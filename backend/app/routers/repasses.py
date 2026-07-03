"""Verbas de repasse: dinheiro que a EPR manda pro Dirceu repassar aos ajudantes.

Não é receita do Dirceu — é caixa de passagem, sem estado (edição/exclusão livres).
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import RepasseEntrada
from app.schemas import RepasseCreate, RepasseOut, RepasseUpdate
from app.security import get_current_user

router = APIRouter(
    prefix="/repasses",
    tags=["financeiro"],
    dependencies=[Depends(get_current_user)],
)


def _get_or_404(db: Session, repasse_id: int) -> RepasseEntrada:
    repasse = db.get(RepasseEntrada, repasse_id)
    if repasse is None:
        raise HTTPException(status_code=404, detail="Verba de repasse não encontrada")
    return repasse


@router.get("", response_model=list[RepasseOut])
def listar(
    de: date | None = None,
    ate: date | None = None,
    db: Session = Depends(get_db),
) -> list[RepasseEntrada]:
    query = db.query(RepasseEntrada)
    if de:
        query = query.filter(RepasseEntrada.data >= de)
    if ate:
        query = query.filter(RepasseEntrada.data <= ate)
    return query.order_by(RepasseEntrada.data.desc(), RepasseEntrada.id.desc()).all()


@router.post("", response_model=RepasseOut, status_code=status.HTTP_201_CREATED)
def criar(payload: RepasseCreate, db: Session = Depends(get_db)) -> RepasseEntrada:
    if payload.valor <= 0:
        raise HTTPException(status_code=422, detail="Valor deve ser maior que zero")
    repasse = RepasseEntrada(data=payload.data, valor=payload.valor, obs=payload.obs)
    db.add(repasse)
    db.commit()
    db.refresh(repasse)
    return repasse


@router.put("/{repasse_id}", response_model=RepasseOut)
def atualizar(
    repasse_id: int, payload: RepasseUpdate, db: Session = Depends(get_db)
) -> RepasseEntrada:
    repasse = _get_or_404(db, repasse_id)
    data = payload.model_dump(exclude_unset=True)
    if "valor" in data:
        if data["valor"] is None or data["valor"] <= 0:
            raise HTTPException(status_code=422, detail="Valor deve ser maior que zero")
        repasse.valor = data["valor"]
    if "data" in data and data["data"] is not None:
        repasse.data = data["data"]
    if "obs" in data:
        repasse.obs = data["obs"]
    db.commit()
    db.refresh(repasse)
    return repasse


@router.delete("/{repasse_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(repasse_id: int, db: Session = Depends(get_db)) -> None:
    repasse = _get_or_404(db, repasse_id)
    db.delete(repasse)
    db.commit()
