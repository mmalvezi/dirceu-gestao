"""Aplicação FastAPI — Dirceu Caldeiraria & Solda (Fase 1: fundação)."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings

app = FastAPI(title="Dirceu — Caldeiraria & Solda")

# CORS a partir das origens configuradas.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Garante que a pasta de mídia existe e a expõe em /media.
os.makedirs(settings.MEDIA_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.MEDIA_DIR), name="media")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": "dirceu-gestao"}
