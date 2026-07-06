"""Vínculo opcional de despesas/adiantamentos a UMA máquina OU UM serviço."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Maquina, Servico


def resolver_vinculo(
    db: Session, maquina_id: int | None, servico_id: int | None
) -> tuple[int | None, str | None, int | None, str | None]:
    """Valida 'máquina OU serviço, não ambos' e devolve os ids + snapshots dos nomes."""
    if maquina_id is not None and servico_id is not None:
        raise HTTPException(
            status_code=422, detail="Vincule a uma máquina OU a um serviço, não ambos"
        )
    maquina_nome = servico_nome = None
    if maquina_id is not None:
        maquina = db.get(Maquina, maquina_id)
        if maquina is None:
            raise HTTPException(status_code=404, detail="Máquina não encontrada")
        maquina_nome = maquina.nome
    if servico_id is not None:
        servico = db.get(Servico, servico_id)
        if servico is None:
            raise HTTPException(status_code=404, detail="Serviço não encontrado")
        servico_nome = servico.descricao
    return maquina_id, maquina_nome, servico_id, servico_nome
