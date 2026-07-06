"""Despesas do Dirceu (deslocamento, alimentação, material...) — CRUD livre, protegido."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Despesa
from app.schemas import DespesaCreate, DespesaOut, DespesaUpdate
from app.security import get_current_user
from app.vinculo import resolver_vinculo

router = APIRouter(
    prefix="/despesas",
    tags=["financeiro"],
    dependencies=[Depends(get_current_user)],
)

CATEGORIAS_VALIDAS = {"deslocamento", "alimentacao", "material", "outros"}


def _get_or_404(db: Session, despesa_id: int) -> Despesa:
    despesa = db.get(Despesa, despesa_id)
    if despesa is None:
        raise HTTPException(status_code=404, detail="Despesa não encontrada")
    return despesa


def _validar_categoria(categoria: str) -> None:
    if categoria not in CATEGORIAS_VALIDAS:
        raise HTTPException(status_code=422, detail="Categoria inválida")


@router.get("", response_model=list[DespesaOut])
def listar(
    de: date | None = None,
    ate: date | None = None,
    categoria: str | None = None,
    maquina_id: int | None = None,
    servico_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[Despesa]:
    query = db.query(Despesa)
    if de:
        query = query.filter(Despesa.data >= de)
    if ate:
        query = query.filter(Despesa.data <= ate)
    if categoria:
        query = query.filter(Despesa.categoria == categoria)
    if maquina_id is not None:
        query = query.filter(Despesa.maquina_id == maquina_id)
    if servico_id is not None:
        query = query.filter(Despesa.servico_id == servico_id)
    return query.order_by(Despesa.data.desc(), Despesa.id.desc()).all()


@router.post("", response_model=DespesaOut, status_code=status.HTTP_201_CREATED)
def criar(payload: DespesaCreate, db: Session = Depends(get_db)) -> Despesa:
    if payload.valor <= 0:
        raise HTTPException(status_code=422, detail="Valor deve ser maior que zero")
    _validar_categoria(payload.categoria)
    maq_id, maq_nome, srv_id, srv_nome = resolver_vinculo(
        db, payload.maquina_id, payload.servico_id
    )
    despesa = Despesa(
        data=payload.data,
        valor=payload.valor,
        categoria=payload.categoria,
        descricao=payload.descricao,
        maquina_id=maq_id,
        maquina_nome=maq_nome,
        servico_id=srv_id,
        servico_nome=srv_nome,
    )
    db.add(despesa)
    db.commit()
    db.refresh(despesa)
    return despesa


@router.put("/{despesa_id}", response_model=DespesaOut)
def atualizar(
    despesa_id: int, payload: DespesaUpdate, db: Session = Depends(get_db)
) -> Despesa:
    despesa = _get_or_404(db, despesa_id)
    dados = payload.model_dump(exclude_unset=True)
    if "valor" in dados:
        if dados["valor"] is None or dados["valor"] <= 0:
            raise HTTPException(status_code=422, detail="Valor deve ser maior que zero")
        despesa.valor = dados["valor"]
    if "categoria" in dados and dados["categoria"] is not None:
        _validar_categoria(dados["categoria"])
        despesa.categoria = dados["categoria"]
    if "data" in dados and dados["data"] is not None:
        despesa.data = dados["data"]
    if "descricao" in dados:
        despesa.descricao = dados["descricao"]
    # Vínculo (excludente): enviar SÓ um dos dois limpa o outro; ambos → resolver valida.
    if "maquina_id" in dados or "servico_id" in dados:
        if "maquina_id" in dados and "servico_id" in dados:
            novo_maq, novo_srv = dados["maquina_id"], dados["servico_id"]
        elif "maquina_id" in dados:
            novo_maq, novo_srv = dados["maquina_id"], None
        else:
            novo_maq, novo_srv = None, dados["servico_id"]
        maq_id, maq_nome, srv_id, srv_nome = resolver_vinculo(db, novo_maq, novo_srv)
        despesa.maquina_id, despesa.maquina_nome = maq_id, maq_nome
        despesa.servico_id, despesa.servico_nome = srv_id, srv_nome
    db.commit()
    db.refresh(despesa)
    return despesa


@router.delete("/{despesa_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(despesa_id: int, db: Session = Depends(get_db)) -> None:
    despesa = _get_or_404(db, despesa_id)
    db.delete(despesa)
    db.commit()
