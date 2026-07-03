"""CRUD de ajudantes (todas as rotas protegidas)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ajudante, DiarioTrabalho
from app.schemas import AjudanteCreate, AjudanteOut, AjudanteUpdate
from app.security import get_current_user

router = APIRouter(
    prefix="/ajudantes",
    tags=["ajudantes"],
    dependencies=[Depends(get_current_user)],
)


def _get_or_404(db: Session, ajudante_id: int) -> Ajudante:
    ajudante = db.get(Ajudante, ajudante_id)
    if ajudante is None:
        raise HTTPException(status_code=404, detail="Ajudante não encontrado")
    return ajudante


@router.get("", response_model=list[AjudanteOut])
def listar(
    q: str | None = None,
    ativo: bool | None = None,
    db: Session = Depends(get_db),
) -> list[Ajudante]:
    query = db.query(Ajudante)
    if q:
        query = query.filter(Ajudante.nome.ilike(f"%{q}%"))
    if ativo is not None:
        query = query.filter(Ajudante.ativo == ativo)
    return query.order_by(Ajudante.nome).all()


@router.post("", response_model=AjudanteOut, status_code=status.HTTP_201_CREATED)
def criar(payload: AjudanteCreate, db: Session = Depends(get_db)) -> Ajudante:
    ajudante = Ajudante(**payload.model_dump())
    db.add(ajudante)
    db.commit()
    db.refresh(ajudante)
    return ajudante


@router.put("/{ajudante_id}", response_model=AjudanteOut)
def atualizar(
    ajudante_id: int, payload: AjudanteUpdate, db: Session = Depends(get_db)
) -> Ajudante:
    ajudante = _get_or_404(db, ajudante_id)
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(ajudante, campo, valor)
    db.commit()
    db.refresh(ajudante)
    return ajudante


@router.delete("/{ajudante_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(ajudante_id: int, db: Session = Depends(get_db)) -> None:
    ajudante = _get_or_404(db, ajudante_id)
    tem_lancamentos = (
        db.query(DiarioTrabalho.id)
        .filter(DiarioTrabalho.ajudante_id == ajudante_id)
        .first()
        is not None
    )
    if tem_lancamentos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ajudante possui lançamentos no diário; inative-o em vez de excluir.",
        )
    db.delete(ajudante)
    db.commit()
