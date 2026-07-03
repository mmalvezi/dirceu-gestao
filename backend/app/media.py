"""Utilitário de imagens: salvar (validar/reduzir/JPEG) e remover arquivos de mídia."""

import os
import uuid

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings


def save_image(upload_file: UploadFile, max_size: int = 1600) -> str:
    """Valida, corrige orientação, reduz e salva como JPEG em MEDIA_DIR.

    Retorna o nome do arquivo gerado (uuid.jpg).
    """
    try:
        img = Image.open(upload_file.file)
        img.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo não é uma imagem válida",
        )

    # Corrige orientação a partir do EXIF (fotos de celular).
    img = ImageOps.exif_transpose(img)

    # JPEG não suporta alfa/paleta — converte tudo para RGB.
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Redimensiona proporcionalmente se exceder max_size (mantém aspecto).
    img.thumbnail((max_size, max_size))

    os.makedirs(settings.MEDIA_DIR, exist_ok=True)
    filename = uuid.uuid4().hex + ".jpg"
    path = os.path.join(settings.MEDIA_DIR, filename)
    img.save(path, format="JPEG", quality=85, optimize=True)
    return filename


def delete_file(filename: str | None) -> None:
    """Remove o arquivo de MEDIA_DIR se existir (silencioso caso contrário)."""
    if not filename:
        return
    path = os.path.join(settings.MEDIA_DIR, filename)
    if os.path.isfile(path):
        os.remove(path)
