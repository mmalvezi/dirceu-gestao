"""Rotas de configuração/branding do sistema (todas protegidas)."""

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.media import delete_file, save_image
from app.models import Config, User
from app.schemas import ConfigOut, ConfigUpdate
from app.security import get_current_user

router = APIRouter(
    prefix="/config",
    tags=["config"],
    dependencies=[Depends(get_current_user)],
)


def get_config(db: Session) -> Config:
    """Retorna a linha única de Config (cria uma por segurança se faltar)."""
    config = db.query(Config).first()
    if config is None:
        config = Config(nome_exibicao="Dirceu — Caldeiraria & Solda")
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def _to_out(config: Config) -> ConfigOut:
    return ConfigOut(
        nome_exibicao=config.nome_exibicao,
        telefone=config.telefone,
        logo_filename=config.logo_filename,
        logo_url=f"/media/{config.logo_filename}" if config.logo_filename else None,
    )


@router.get("", response_model=ConfigOut)
def read_config(db: Session = Depends(get_db)) -> ConfigOut:
    return _to_out(get_config(db))


@router.put("", response_model=ConfigOut)
def update_config(
    payload: ConfigUpdate, db: Session = Depends(get_db)
) -> ConfigOut:
    config = get_config(db)
    data = payload.model_dump(exclude_unset=True)
    if "nome_exibicao" in data and data["nome_exibicao"] is not None:
        config.nome_exibicao = data["nome_exibicao"]
    if "telefone" in data:
        config.telefone = data["telefone"]
    db.commit()
    db.refresh(config)
    return _to_out(config)


@router.post("/logo", response_model=ConfigOut)
def upload_logo(
    file: UploadFile, db: Session = Depends(get_db)
) -> ConfigOut:
    config = get_config(db)
    novo_nome = save_image(file)
    anterior = config.logo_filename
    config.logo_filename = novo_nome
    db.commit()
    db.refresh(config)
    # Só apaga o antigo depois de gravar o novo (evita perder logo se algo falhar).
    if anterior and anterior != novo_nome:
        delete_file(anterior)
    return _to_out(config)


@router.delete("/logo", response_model=ConfigOut)
def delete_logo(db: Session = Depends(get_db)) -> ConfigOut:
    config = get_config(db)
    anterior = config.logo_filename
    config.logo_filename = None
    db.commit()
    db.refresh(config)
    delete_file(anterior)
    return _to_out(config)
