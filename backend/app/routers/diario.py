"""Diário de obra — o núcleo do sistema (rotas aninhadas na máquina, protegidas).

Um lançamento = UM DIA numa máquina: data + descrição + lista de trabalhos
(quem trabalhou: ajudante, horas, valor, origem do dinheiro). Snapshot do nome
do ajudante gravado no momento do lançamento.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Ajudante, DiarioEntrada, DiarioTrabalho, Maquina
from app.schemas import (
    DiarioEntradaIn,
    DiarioEntradaOut,
    DiarioEntradaSalvaOut,
    TrabalhoIn,
    TrabalhoOut,
)
from app.security import get_current_user

router = APIRouter(
    prefix="/maquinas",
    tags=["diario"],
    dependencies=[Depends(get_current_user)],
)

ORIGENS_VALIDAS = {"repasse", "epr_direto", "bolso"}


def montar_entrada_out(entrada: DiarioEntrada) -> DiarioEntradaOut:
    """Monta a saída de uma entrada com trabalhos ordenados por id e totais."""
    trabalhos = sorted(entrada.trabalhos, key=lambda t: t.id)
    total_horas = sum((Decimal(str(t.horas)) for t in trabalhos), Decimal("0"))
    total_valor = sum((Decimal(str(t.valor)) for t in trabalhos), Decimal("0"))
    return DiarioEntradaOut(
        id=entrada.id,
        maquina_id=entrada.maquina_id,
        data=entrada.data,
        descricao=entrada.descricao,
        trabalhos=[
            TrabalhoOut(
                id=t.id,
                ajudante_id=t.ajudante_id,
                ajudante_nome=t.ajudante_nome,
                horas=float(t.horas),
                valor=float(t.valor),
                origem=t.origem,
                proprio=t.proprio,
            )
            for t in trabalhos
        ],
        total_horas=float(total_horas),
        total_valor=float(total_valor),
    )


def _get_maquina_lancavel(db: Session, maquina_id: int) -> Maquina:
    """Retorna a máquina (404 se não existe, 409 se fechada — não recebe lançamentos)."""
    maquina = db.get(Maquina, maquina_id)
    if maquina is None:
        raise HTTPException(status_code=404, detail="Máquina não encontrada")
    if maquina.status == "fechada":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Máquina fechada não recebe lançamentos.",
        )
    return maquina


def _validar_entrada(payload: DiarioEntradaIn, db: Session) -> list[DiarioTrabalho]:
    """Valida descrição e trabalhos; devolve os DiarioTrabalho já com snapshot do nome."""
    if not payload.descricao or not payload.descricao.strip():
        raise HTTPException(status_code=422, detail="Descrição obrigatória")

    if not payload.trabalhos:
        raise HTTPException(status_code=422, detail="Lance pelo menos um trabalho")

    return [_montar_trabalho(t, db) for t in payload.trabalhos]


def _montar_trabalho(t: TrabalhoIn, db: Session) -> DiarioTrabalho:
    # "Eu trabalhei": Dirceu com horas e SEM valor (remuneração = empreita).
    if t.proprio:
        if t.ajudante_id is not None:
            raise HTTPException(
                status_code=422, detail="Trabalho próprio não leva ajudante vinculado"
            )
        return DiarioTrabalho(
            ajudante_id=None,
            ajudante_nome="Dirceu",
            horas=t.horas,
            valor=0,  # forçado: horas próprias não geram custo/pagamento
            origem="proprio",
            proprio=True,
        )

    if t.origem not in ORIGENS_VALIDAS:
        raise HTTPException(status_code=422, detail="Origem inválida")

    if t.ajudante_id is not None:
        # Com id: usa SEMPRE o nome do cadastro como snapshot (ignora o nome enviado).
        ajudante = db.get(Ajudante, t.ajudante_id)
        if ajudante is None:
            raise HTTPException(status_code=404, detail="Ajudante não encontrado")
        nome = ajudante.nome
    else:
        # Sem id: o nome é obrigatório.
        if not t.ajudante_nome or not t.ajudante_nome.strip():
            raise HTTPException(
                status_code=422, detail="Informe o ajudante ou o nome"
            )
        nome = t.ajudante_nome.strip()

    return DiarioTrabalho(
        ajudante_id=t.ajudante_id,
        ajudante_nome=nome,
        horas=t.horas,
        valor=t.valor,
        origem=t.origem,
    )


def _com_aviso(entrada: DiarioEntrada, maquina: Maquina) -> DiarioEntradaSalvaOut:
    aviso = (
        "Lançamento em máquina finalizada."
        if maquina.status == "finalizada"
        else None
    )
    base = montar_entrada_out(entrada)
    return DiarioEntradaSalvaOut(**base.model_dump(), aviso=aviso)


@router.post(
    "/{maquina_id}/diario",
    response_model=DiarioEntradaSalvaOut,
    status_code=status.HTTP_201_CREATED,
)
def criar_entrada(
    maquina_id: int, payload: DiarioEntradaIn, db: Session = Depends(get_db)
) -> DiarioEntradaSalvaOut:
    maquina = _get_maquina_lancavel(db, maquina_id)
    trabalhos = _validar_entrada(payload, db)

    entrada = DiarioEntrada(
        maquina_id=maquina.id,
        data=payload.data,
        descricao=payload.descricao.strip(),
    )
    entrada.trabalhos.extend(trabalhos)
    db.add(entrada)
    db.commit()
    db.refresh(entrada)
    return _com_aviso(entrada, maquina)


@router.put(
    "/{maquina_id}/diario/{entrada_id}", response_model=DiarioEntradaSalvaOut
)
def atualizar_entrada(
    maquina_id: int,
    entrada_id: int,
    payload: DiarioEntradaIn,
    db: Session = Depends(get_db),
) -> DiarioEntradaSalvaOut:
    maquina = _get_maquina_lancavel(db, maquina_id)

    entrada = db.get(DiarioEntrada, entrada_id)
    if entrada is None or entrada.maquina_id != maquina_id:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")

    novos = _validar_entrada(payload, db)

    entrada.data = payload.data
    entrada.descricao = payload.descricao.strip()
    # Substituição em massa: apaga os trabalhos antigos e recria a partir da lista.
    entrada.trabalhos.clear()
    db.flush()
    entrada.trabalhos.extend(novos)
    db.commit()
    db.refresh(entrada)
    return _com_aviso(entrada, maquina)


@router.delete(
    "/{maquina_id}/diario/{entrada_id}", status_code=status.HTTP_204_NO_CONTENT
)
def excluir_entrada(
    maquina_id: int, entrada_id: int, db: Session = Depends(get_db)
) -> None:
    _get_maquina_lancavel(db, maquina_id)  # 404/409 se máquina inexistente/fechada

    entrada = db.get(DiarioEntrada, entrada_id)
    if entrada is None or entrada.maquina_id != maquina_id:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")

    db.delete(entrada)  # CASCADE remove os trabalhos
    db.commit()


def listar_diario(db: Session, maquina_id: int) -> list[DiarioEntradaOut]:
    """Diário completo da máquina, mais recente primeiro (data desc, id desc)."""
    entradas = (
        db.query(DiarioEntrada)
        .filter(DiarioEntrada.maquina_id == maquina_id)
        .options(selectinload(DiarioEntrada.trabalhos))
        .order_by(DiarioEntrada.data.desc(), DiarioEntrada.id.desc())
        .all()
    )
    return [montar_entrada_out(e) for e in entradas]
