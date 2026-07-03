"""Segurança: hash de senha (bcrypt direto, SEM passlib) e JWT (PyJWT)."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def hash_password(senha: str) -> str:
    """Gera o hash bcrypt da senha (bcrypt direto — sem passlib)."""
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(senha: str, hashed: str) -> bool:
    """Confere a senha contra o hash bcrypt."""
    return bcrypt.checkpw(senha.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict) -> str:
    """Cria um JWT HS256 com 'sub' e 'exp' (agora + expiração configurada)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Dependency: valida o JWT e devolve o User; caso contrário, 401."""
    nao_autorizado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autorizado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise nao_autorizado
    except jwt.PyJWTError:
        raise nao_autorizado

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise nao_autorizado
    return user
