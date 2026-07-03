"""Seed idempotente rodado no startup: cria a linha de config e o usuário admin.

Senha hasheada com bcrypt DIRETO (sem passlib — evita conflito com bcrypt 4.x+).
"""

import bcrypt

from app.config import settings
from app.database import SessionLocal
from app.models import Config, User


def run_seed() -> None:
    db = SessionLocal()
    try:
        if db.query(Config).first() is None:
            db.add(Config(nome_exibicao="Dirceu — Caldeiraria & Solda"))
            db.commit()
            print("[seed] linha de config criada")

        if db.query(User).filter(User.username == settings.ADMIN_USERNAME).first() is None:
            hashed = bcrypt.hashpw(
                settings.ADMIN_PASSWORD.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")
            db.add(User(username=settings.ADMIN_USERNAME, hashed_password=hashed))
            db.commit()
            print(f"[seed] usuário admin '{settings.ADMIN_USERNAME}' criado")
    finally:
        db.close()
